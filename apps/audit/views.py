from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.accounts.permissions import admin_required
from apps.core.pagination import extra_query, paginate, per_page_value

from .models import AuditEvent


@admin_required
@require_GET
def audit_list(request):
    query = request.GET.get("q", "").strip()
    action = request.GET.get("action", "").strip()
    events = AuditEvent.objects.select_related("actor")
    if query:
        events = events.filter(
            Q(summary__icontains=query)
            | Q(actor_name__icontains=query)
            | Q(object_label__icontains=query)
            | Q(object_id__icontains=query)
        )
    if action in AuditEvent.Action.values:
        events = events.filter(action=action)
    page = paginate(request, events)
    return render(
        request,
        "audit/list.html",
        {
            "page_title": "Audit Log",
            "events": page,
            "query": query,
            "action": action,
            "actions": AuditEvent.Action.choices,
            "extra_query": extra_query(request),
            "per_page": per_page_value(request),
        },
    )
