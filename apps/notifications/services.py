import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.billing.services import due_soon_enrollments, overdue_enrollments, period_balance
from apps.core.constants import format_money
from apps.core.services import get_school_settings

from .models import NotificationLog

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def telegram_credentials():
    school = get_school_settings()
    token = (school.telegram_bot_token or "").strip() or (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "")
    chat_id = (school.telegram_admin_chat_id or "").strip() or (getattr(settings, "TELEGRAM_CHAT_ID", "") or "")
    return token, chat_id


def telegram_configured():
    token, chat_id = telegram_credentials()
    return bool(token and chat_id)


def _explain_telegram_error(description):
    text = (description or "").lower()
    if "chat not found" in text:
        return "រកមិនឃើញ Admin chat។ បើក Bot រួចចុច Start សិន បន្ទាប់មកយក Chat ID ថ្មី។"
    if "unauthorized" in text:
        return "Bot Token ខុស ឬផុតសុពលភាព។"
    if "blocked" in text:
        return "Admin បានទប់ Bot។ បើក Bot រួចចុច Start ម្ដងទៀត។"
    if "bot can't initiate conversation" in text:
        return "Bot មិនអាចផ្ញើមុនបានទេ។ បើក Bot រួចចុច Start សិន។"
    return f"មិនអាចផ្ញើ Telegram៖ {description or 'បដិសេធសារ'}"


def _telegram_request(method, payload=None):
    token, _chat_id = telegram_credentials()
    if not token:
        raise ValidationError("មិនទាន់កំណត់ Telegram Bot Token។")
    data = urllib.parse.urlencode(payload).encode() if payload else None
    request = urllib.request.Request(
        TELEGRAM_API.format(token=token, method=method),
        data=data,
        method="POST" if data else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {}
        raise ValidationError(_explain_telegram_error(body.get("description") or exc.reason)) from exc
    except urllib.error.URLError as exc:
        raise ValidationError(f"មិនអាចភ្ជាប់ Telegram៖ {exc.reason}") from exc
    if not body.get("ok"):
        raise ValidationError(_explain_telegram_error(body.get("description")))
    return body


def send_telegram_message(text, *, user=None):
    token, chat_id = telegram_credentials()
    if not token or not chat_id:
        raise ValidationError("មិនទាន់កំណត់ Telegram Bot Token ឬ Admin Chat ID។")
    return _telegram_request(
        "sendMessage",
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"},
    )


def detect_admin_chat_id():
    body = _telegram_request("getUpdates")
    for update in reversed(body.get("result") or []):
        for key in ("message", "edited_message", "my_chat_member", "chat_member"):
            chat = (update.get(key) or {}).get("chat") or {}
            chat_id = chat.get("id")
            if chat_id:
                return str(chat_id)
    raise ValidationError("មិនទាន់មានសារពី Admin។ បើក Bot រួចចុច Start សិន។")


def apply_detected_chat_id(*, user=None):
    chat_id = detect_admin_chat_id()
    school = get_school_settings()
    school.telegram_admin_chat_id = chat_id
    school.save(update_fields=["telegram_admin_chat_id"])
    log_event(
        action=AuditEvent.Action.SETTINGS_UPDATED,
        summary=f"យក Telegram Admin Chat ID {chat_id}",
        user=user,
        obj=school,
    )
    return chat_id


def _format_alert(enrollment, kind, school, days):
    due = enrollment.next_due_date.strftime("%d/%m/%Y") if enrollment.next_due_date else "—"
    student = enrollment.student
    status = "ហួស Due Date" if kind == NotificationLog.Kind.OVERDUE else f"ជិតដល់ Due Date ({days} ថ្ងៃ)"
    fee = format_money(enrollment.course_class.course.default_fee, enrollment.course_class.course.currency)
    remaining = period_balance(enrollment)
    remaining_display = format_money(remaining["remaining"], remaining["currency"])
    return (
        f"{school.school_name}\n"
        f"ជូនដំណឹងថ្លៃសិក្សា · {status}\n"
        f"សិស្ស៖ {student.name_kh} ({student.student_id})\n"
        f"ថ្នាក់៖ {enrollment.course_class.name}\n"
        f"ថ្លៃវគ្គ៖ {fee}\n"
        f"នៅជំពាក់៖ {remaining_display}\n"
        f"Due Date៖ {due}"
    )


def _already_sent(enrollment, kind, today):
    return NotificationLog.objects.filter(
        enrollment=enrollment,
        kind=kind,
        sent_on=today,
        status=NotificationLog.Status.SENT,
    ).exists()


def _record(enrollment, kind, today, status, message, error=""):
    log, _created = NotificationLog.objects.update_or_create(
        enrollment=enrollment,
        kind=kind,
        sent_on=today,
        defaults={
            "channel": "telegram",
            "status": status,
            "message": message,
            "error": error[:255],
        },
    )
    return log


def send_due_alerts(*, user=None, today=None):
    today = today or timezone.localdate()
    school = get_school_settings()
    days = school.reminder_days_before_due or 3
    sent = 0
    failed = 0
    skipped = 0

    targets = [(NotificationLog.Kind.DUE_SOON, due_soon_enrollments(today, days=days))]
    if school.overdue_alert_daily:
        targets.append((NotificationLog.Kind.OVERDUE, overdue_enrollments(today)))

    if not telegram_configured():
        raise ValidationError("មិនទាន់កំណត់ Telegram Bot Token ឬ Admin Chat ID។")

    for kind, queryset in targets:
        for enrollment in queryset:
            if _already_sent(enrollment, kind, today):
                skipped += 1
                continue
            message = _format_alert(enrollment, kind, school, days)
            try:
                send_telegram_message(message, user=user)
                _record(enrollment, kind, today, NotificationLog.Status.SENT, message)
                sent += 1
            except ValidationError as exc:
                error = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
                _record(enrollment, kind, today, NotificationLog.Status.FAILED, message, error)
                log_event(
                    action=AuditEvent.Action.TELEGRAM_FAILED,
                    summary=f"ផ្ញើ Telegram បរាជ័យ · {enrollment.student}",
                    user=user,
                    obj=enrollment,
                    extra={"error": error},
                )
                failed += 1
    if sent or failed:
        log_event(
            action=AuditEvent.Action.TELEGRAM_SENT if sent else AuditEvent.Action.TELEGRAM_FAILED,
            summary=f"ការជូនដំណឹង Due Date៖ ផ្ញើ {sent} · បរាជ័យ {failed} · រំលង {skipped}",
            user=user,
        )
    return {"sent": sent, "failed": failed, "skipped": skipped}


def send_test_message(*, user=None):
    school = get_school_settings()
    text = f"{school.school_name}\nសារសាកល្បង Telegram · Admin chat តែប៉ុណ្ណោះ។"
    send_telegram_message(text, user=user)
    log_event(
        action=AuditEvent.Action.TELEGRAM_SENT,
        summary="សារសាកល្បង Telegram ទៅ Admin chat",
        user=user,
    )
    NotificationLog.objects.create(
        enrollment=None,
        kind=NotificationLog.Kind.TEST,
        sent_on=timezone.localdate(),
        status=NotificationLog.Status.SENT,
        message=text,
    )
    return text
