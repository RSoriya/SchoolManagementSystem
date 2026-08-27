from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.permissions import admin_required
from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.notifications.models import NotificationLog
from apps.notifications.services import send_due_alerts, send_test_message, telegram_configured

from .backup import backup_records, keep_days
from .forms import SchoolSettingsForm
from .models import PaymentMethod
from .services import get_school_settings


@require_GET
def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", {"reason": reason}, status=403)


def _settings_context(form):
    return {
        "page_title": "ការកំណត់",
        "form": form,
        "payment_methods": PaymentMethod.objects.all(),
        "telegram_ready": telegram_configured(),
        "notification_logs": NotificationLog.objects.select_related(
            "enrollment__student",
            "enrollment__course_class",
        )[:8],
        "backups": backup_records(),
        "backup_keep_days": keep_days(),
    }


def _error_message(exc):
    if hasattr(exc, "messages") and exc.messages:
        return exc.messages[0]
    return str(exc)


@admin_required
@require_http_methods(["GET", "POST"])
def school_settings(request):
    school = get_school_settings()
    form = SchoolSettingsForm(request.POST or None, request.FILES or None, instance=school)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_event(
            action=AuditEvent.Action.SETTINGS_UPDATED,
            summary="កែការកំណត់សាលា និង Telegram",
            user=request.user,
            obj=school,
        )
        messages.success(request, "បានរក្សាទុកការកំណត់សាលា។")
        return redirect("core:settings")
    return render(request, "core/settings.html", _settings_context(form))


@admin_required
@require_POST
def telegram_test(request):
    try:
        send_test_message(user=request.user)
        messages.success(request, "បានផ្ញើសារសាកល្បងទៅ Admin chat។")
    except ValidationError as exc:
        messages.error(request, _error_message(exc))
    return redirect("core:settings")


@admin_required
@require_POST
def telegram_send_alerts(request):
    try:
        result = send_due_alerts(user=request.user)
        messages.success(
            request,
            f"ការជូនដំណឹង Due Date៖ ផ្ញើ {result['sent']} · បរាជ័យ {result['failed']} · រំលង {result['skipped']}",
        )
    except ValidationError as exc:
        messages.error(request, _error_message(exc))
    return redirect("core:settings")
