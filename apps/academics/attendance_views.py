from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET


@require_GET
def attendance_list(request):
    return redirect("academics:class_list")


@require_GET
def attendance_sheet(request, pk):
    target = reverse("academics:class_attendance", args=[pk])
    attended_on = (request.GET.get("date") or "").strip()
    if attended_on:
        target = f"{target}?from={attended_on}&to={attended_on}"
    return redirect(target)
