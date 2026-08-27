import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.billing.services import due_soon_enrollments, overdue_enrollments
from apps.core.constants import format_money
from apps.core.services import get_school_settings

from .models import NotificationLog

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def telegram_credentials():
    school = get_school_settings()
    token = (school.telegram_bot_token or "").strip() or (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "")
    chat_id = (school.telegram_admin_chat_id or "").strip() or (getattr(settings, "TELEGRAM_CHAT_ID", "") or "")
    return token, chat_id


def telegram_configured():
    token, chat_id = telegram_credentials()
    return bool(token and chat_id)


def send_telegram_message(text, *, user=None):
    token, chat_id = telegram_credentials()
    if not token or not chat_id:
        raise ValidationError("មិនទាន់កំណត់ Telegram Bot Token ឬ Admin Chat ID។")
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    ).encode()
    request = urllib.request.Request(
        TELEGRAM_API.format(token=token),
        data=payload,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ValidationError(f"មិនអាចផ្ញើ Telegram៖ {exc.reason}") from exc
    if not body.get("ok"):
        raise ValidationError(body.get("description") or "Telegram បដិសេធសារ។")
    return body


def _format_alert(enrollment, kind, school, days):
    due = enrollment.next_due_date.strftime("%d/%m/%Y") if enrollment.next_due_date else "—"
    student = enrollment.student
    status = "ហួស Due Date" if kind == NotificationLog.Kind.OVERDUE else f"ជិតដល់ Due Date ({days} ថ្ងៃ)"
    fee = format_money(enrollment.course_class.course.default_fee, enrollment.course_class.course.currency)
    return (
        f"{school.school_name}\n"
        f"ជូនដំណឹងថ្លៃសិក្សា · {status}\n"
        f"សិស្ស៖ {student.name_kh} ({student.student_id})\n"
        f"ថ្នាក់៖ {enrollment.course_class.name}\n"
        f"ថ្លៃវគ្គ៖ {fee}\n"
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
