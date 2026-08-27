from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.core.pagination import extra_query, paginate, per_page_value

from .forms import AdminAuthenticationForm, AdminUserForm
from .models import User
from .payloads import user_payload
from .permissions import admin_required
from .services import can_deactivate, ensure_admin_group


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


@method_decorator(never_cache, name="dispatch")
class ThrottledLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = AdminAuthenticationForm
    redirect_authenticated_user = True

    def _throttle_key(self):
        return f"login-fail:{_client_ip(self.request)}"

    def post(self, request, *args, **kwargs):
        from django.conf import settings

        failures = cache.get(self._throttle_key(), 0)
        if failures >= getattr(settings, "LOGIN_FAILURE_LIMIT", 5):
            form = self.get_form_class()(request, data=request.POST)
            return self.render_to_response(
                self.get_context_data(form=form, login_locked=True)
            )
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        from django.conf import settings

        key = self._throttle_key()
        window = getattr(settings, "LOGIN_FAILURE_WINDOW", 900)
        cache.set(key, cache.get(key, 0) + 1, window)
        username = self.request.POST.get("username", "")
        log_event(
            action=AuditEvent.Action.LOGIN_FAILED,
            summary=f"ចូលប្រព័ន្ធបរាជ័យ · {username or '—'}",
            extra={"ip": _client_ip(self.request), "username": username[:150]},
        )
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._throttle_key())
        ensure_admin_group(form.get_user())
        return super().form_valid(form)


def _user_list_response(request, form=None, open_form_modal=False):
    query = request.GET.get("q", "").strip()
    users = User.objects.order_by("username")
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(full_name_kh__icontains=query)
            | Q(phone_number__icontains=query)
            | Q(email__icontains=query)
        )
    page = paginate(request, users)
    return render(
        request,
        "accounts/list.html",
        {
            "page_title": "អ្នកប្រើប្រាស់",
            "users": page,
            "query": query,
            "form": form or AdminUserForm(),
            "payloads": {str(item.pk): user_payload(item) for item in page.object_list},
            "open_form_modal": open_form_modal,
            "create_url": reverse("users:create"),
            "current_user_id": request.user.pk,
            "per_page": per_page_value(request),
            "extra_query": extra_query(request),
        },
    )


@admin_required
@require_GET
def user_list(request):
    return _user_list_response(request)


@admin_required
@require_http_methods(["GET", "POST"])
def user_create(request):
    form = AdminUserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        ensure_admin_group(user)
        log_event(
            action=AuditEvent.Action.USER_CREATED,
            summary=f"បង្កើតអ្នកប្រើ {user.username}",
            user=request.user,
            obj=user,
        )
        messages.success(request, f"បានបង្កើតអ្នកប្រើ {user.username}។")
        return redirect("users:list")
    if request.method == "POST" and request.POST.get("from_modal"):
        return _user_list_response(request, form=form, open_form_modal=True)
    return render(
        request,
        "accounts/form.html",
        {"page_title": "បន្ថែមអ្នកប្រើ", "form": form, "account": None},
    )


@admin_required
@require_http_methods(["GET", "POST"])
def user_edit(request, pk):
    account = get_object_or_404(User, pk=pk)
    form = AdminUserForm(request.POST or None, instance=account)
    if request.method == "POST" and form.is_valid():
        if account.pk == request.user.pk:
            form.instance.is_active = True
        elif (
            account.is_active
            and not form.cleaned_data.get("is_active")
            and not can_deactivate(account, request.user)
        ):
            form.add_error("is_active", "មិនអាចផ្អាកគណនីនេះបានទេ។")
        if not form.errors:
            user = form.save()
            ensure_admin_group(user)
            log_event(
                action=AuditEvent.Action.USER_UPDATED,
                summary=f"កែអ្នកប្រើ {user.username}",
                user=request.user,
                obj=user,
            )
            messages.success(request, "បានរក្សាទុកអ្នកប្រើប្រាស់។")
            return redirect("users:list")
    if request.method == "POST" and request.POST.get("from_modal"):
        return _user_list_response(request, form=form, open_form_modal=True)
    return render(
        request,
        "accounts/form.html",
        {"page_title": f"កែអ្នកប្រើ · {account.username}", "form": form, "account": account},
    )


@admin_required
@require_POST
def user_deactivate(request, pk):
    account = get_object_or_404(User, pk=pk)
    if not can_deactivate(account, request.user):
        messages.error(request, "មិនអាចផ្អាកគណនីនេះបានទេ។")
        return redirect("users:list")
    account.is_active = False
    account.save(update_fields=["is_active"])
    log_event(
        action=AuditEvent.Action.USER_DEACTIVATED,
        summary=f"ផ្អាកអ្នកប្រើ {account.username}",
        user=request.user,
        obj=account,
    )
    messages.success(request, "បានផ្អាកគណនី។ ប្រវត្តិនៅតែរក្សាទុក។")
    return redirect("users:list")
