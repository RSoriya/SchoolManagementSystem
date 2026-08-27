from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from apps.academics.models import Course, CourseClass, Enrollment
from apps.accounts.permissions import admin_required
from apps.billing.models import Payment
from apps.billing.services import (
    due_soon_enrollments,
    overdue_enrollments,
    revenue_in_month,
    revenue_in_year,
    revenue_on,
    unpaid_enrollments,
)
from apps.core.constants import format_money
from apps.students.models import Student


@admin_required
def index(request):
    today = timezone.localdate()
    active_filter = Q(enrollments__status=Enrollment.Status.ACTIVE)
    courses = list(
        Course.objects.filter(is_active=True)
        .annotate(
            student_count=Count(
                "classes__enrollments",
                filter=Q(classes__enrollments__status=Enrollment.Status.ACTIVE),
            )
        )
        .order_by("-student_count", "name")[:8]
    )
    max_count = max((course.student_count for course in courses), default=0) or 1
    display_name = (
        request.user.get_full_name()
        or getattr(request.user, "full_name_kh", "")
        or request.user.username
    )
    unpaid = unpaid_enrollments(today)
    overdue = overdue_enrollments(today)
    due_soon = due_soon_enrollments(today)
    context = {
        "page_title": "ផ្ទាំងគ្រប់គ្រង",
        "greeting_name": display_name,
        "today": today,
        "stats": {
            "total_students": Student.objects.count(),
            "active_students": Student.objects.filter(active_filter).distinct().count(),
            "total_courses": Course.objects.filter(is_active=True).count(),
            "total_classes": CourseClass.objects.filter(is_active=True).count(),
            "unpaid_students": unpaid.values("student_id").distinct().count(),
            "overdue_students": overdue.values("student_id").distinct().count(),
            "due_soon_students": due_soon.values("student_id").distinct().count(),
            "today_usd": format_money(revenue_on(today, "USD"), "USD"),
            "today_khr": format_money(revenue_on(today, "KHR"), "KHR"),
            "month_usd": format_money(revenue_in_month(today, "USD"), "USD"),
            "month_khr": format_money(revenue_in_month(today, "KHR"), "KHR"),
            "year_usd": format_money(revenue_in_year(today, "USD"), "USD"),
            "year_khr": format_money(revenue_in_year(today, "KHR"), "KHR"),
        },
        "course_bars": [
            {
                "course": course,
                "percent": int(course.student_count * 100 / max_count),
            }
            for course in courses
        ],
        "unpaid_enrollments": unpaid[:8],
        "due_soon_enrollments": due_soon[:8],
        "overdue_enrollments": overdue[:8],
        "recent_payments": Payment.objects.select_related(
            "student",
            "course_class",
            "receipt",
        )
        .filter(status=Payment.Status.COMPLETED)
        .order_by("-paid_on", "-created_at")[:6],
        "recent_students": Student.objects.order_by("-created_at")[:6],
        "recent_enrollments": Enrollment.objects.select_related(
            "student", "course_class"
        ).order_by("-created_at")[:6],
    }
    return render(request, "dashboard/index.html", context)
