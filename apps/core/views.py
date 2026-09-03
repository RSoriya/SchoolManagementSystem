from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.permissions import admin_required
from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.notifications.models import NotificationLog
from apps.notifications.services import (
    apply_detected_chat_id,
    send_due_alerts,
    send_test_message,
    telegram_configured,
    telegram_credentials,
)

from .backup import backup_records, keep_days
from .forms import PaymentMethodForm, SchoolSettingsForm
from .models import PaymentMethod
from .services import get_school_settings


@require_GET
def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", {"reason": reason}, status=403)


def _method_payload(method):
    return {
        "name": method.name,
        "code": method.code,
        "requires_reference": method.requires_reference,
        "is_active": method.is_active,
        "sort_order": method.sort_order,
        "edit_url": reverse("core:payment_method_edit", args=[method.pk]),
        "delete_url": reverse("core:payment_method_delete", args=[method.pk]),
        "label": method.name,
    }


def _settings_context(form, method_form=None, open_form_modal=False, method_form_action=None):
    methods = list(PaymentMethod.objects.all())
    return {
        "page_title": "ការកំណត់",
        "form": form,
        "payment_methods": methods,
        "method_form": method_form or PaymentMethodForm(),
        "method_payloads": {str(item.pk): _method_payload(item) for item in methods},
        "method_create_url": reverse("core:payment_method_create"),
        "method_form_action": method_form_action or reverse("core:payment_method_create"),
        "open_form_modal": open_form_modal,
        "telegram_ready": telegram_configured(),
        "telegram_token_ready": bool(telegram_credentials()[0]),
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
@require_http_methods(["GET", "POST"])
def payment_method_create(request):
    if request.method == "GET":
        return redirect(f"{reverse('core:settings')}?open=add")
    form = PaymentMethodForm(request.POST)
    if form.is_valid():
        method = form.save()
        messages.success(request, f"បានបន្ថែមវិធីបង់ប្រាក់ {method.name}។")
        return redirect("core:settings")
    school_form = SchoolSettingsForm(instance=get_school_settings())
    return render(
        request,
        "core/settings.html",
        _settings_context(school_form, method_form=form, open_form_modal=True),
    )


@admin_required
@require_http_methods(["GET", "POST"])
def payment_method_edit(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk)
    if request.method == "GET":
        return redirect(f"{reverse('core:settings')}?edit={method.pk}")
    form = PaymentMethodForm(request.POST, instance=method)
    if form.is_valid():
        form.save()
        messages.success(request, f"បានកែវិធីបង់ប្រាក់ {method.name}។")
        return redirect("core:settings")
    school_form = SchoolSettingsForm(instance=get_school_settings())
    return render(
        request,
        "core/settings.html",
        _settings_context(
            school_form,
            method_form=form,
            open_form_modal=True,
            method_form_action=reverse("core:payment_method_edit", args=[method.pk]),
        ),
    )


@admin_required
@require_POST
def payment_method_delete(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk)
    if method.payments.exists() or method.refunds.exists():
        messages.error(request, "មិនអាចលុបវិធីបង់ដែលមានប្រវត្តិបង់ ឬសងប្រាក់។")
        return redirect("core:settings")
    name = method.name
    log_event(
        action=AuditEvent.Action.SETTINGS_UPDATED,
        summary=f"លុបវិធីបង់ប្រាក់ {name}",
        user=request.user,
        obj=method,
    )
    try:
        method.delete()
    except ProtectedError:
        messages.error(request, "មិនអាចលុបវិធីបង់នេះបានទេ។")
        return redirect("core:settings")
    messages.success(request, f"បានលុបវិធីបង់ប្រាក់ {name}។")
    return redirect("core:settings")


@admin_required
@require_POST
def telegram_detect_chat(request):
    try:
        chat_id = apply_detected_chat_id(user=request.user)
        messages.success(request, f"បានយក Chat ID {chat_id}។ សូមចុចផ្ញើសារសាកល្បង។")
    except ValidationError as exc:
        messages.error(request, _error_message(exc))
    return redirect("core:settings")


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
