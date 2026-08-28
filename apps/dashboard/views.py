from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from apps.academics.attendance import is_study_day
from apps.academics.models import AttendanceRecord, Course, CourseClass, Enrollment
from apps.accounts.permissions import staff_required
from apps.accounts.roles import is_teacher, user_has_perm
from apps.accounts.scoping import visible_classes, visible_courses, visible_enrollments, visible_students
from apps.billing.models import Payment
from apps.billing.services import (
    attach_period_balances,
    due_soon_enrollments,
    overdue_enrollments,
    revenue_in_month,
    revenue_in_year,
    revenue_on,
    unpaid_enrollments,
)
from apps.core.constants import format_money


def _attendance_today(user, classes, today):
    if not user_has_perm(user, "academics.view_attendancerecord"):
        return []
    study_classes = [
        course_class
        for course_class in classes.select_related("course").order_by("name")
        if is_study_day(course_class, today)
    ]
    marked_ids = set(
        AttendanceRecord.objects.filter(
            attended_on=today,
            course_class_id__in=[course_class.pk for course_class in study_classes],
        ).values_list("course_class_id", flat=True)
    )
    return [
        {"course_class": course_class, "marked": course_class.pk in marked_ids}
        for course_class in study_classes
    ]


@staff_required
def index(request):
    today = timezone.localdate()
    user = request.user
    show_billing = user_has_perm(user, "billing.view_payment")
    teacher = is_teacher(user)
    active_filter = Q(enrollments__status=Enrollment.Status.ACTIVE)
    students = visible_students(user)
    classes = visible_classes(user, CourseClass.objects.filter(is_active=True))
    courses = visible_courses(user, Course.objects.filter(is_active=True))
    course_bars_qs = list(
        courses.annotate(
            student_count=Count(
                "classes__enrollments",
                filter=Q(classes__enrollments__status=Enrollment.Status.ACTIVE)
                & (Q(classes__instructor=user) if teacher else Q()),
            )
        ).order_by("-student_count", "name")[:8]
    )
    max_count = max((course.student_count for course in course_bars_qs), default=0) or 1
    display_name = (
        user.get_full_name()
        or getattr(user, "full_name_kh", "")
        or user.username
    )
    unpaid = unpaid_enrollments(today) if show_billing else Enrollment.objects.none()
    overdue = overdue_enrollments(today) if show_billing else Enrollment.objects.none()
    due_soon = due_soon_enrollments(today) if show_billing else Enrollment.objects.none()
    if teacher:
        unpaid = unpaid.filter(course_class__instructor=user)
        overdue = overdue.filter(course_class__instructor=user)
        due_soon = due_soon.filter(course_class__instructor=user)
    unpaid_rows = attach_period_balances(unpaid[:8]) if show_billing else []
    context = {
        "page_title": "ផ្ទាំងគ្រប់គ្រង",
        "greeting_name": display_name,
        "today": today,
        "show_billing": show_billing,
        "stats": {
            "total_students": students.count(),
            "active_students": students.filter(active_filter).distinct().count(),
            "total_courses": courses.count(),
            "total_classes": classes.count(),
            "unpaid_students": unpaid.values("student_id").distinct().count() if show_billing else 0,
            "overdue_students": overdue.values("student_id").distinct().count() if show_billing else 0,
            "due_soon_students": due_soon.values("student_id").distinct().count() if show_billing else 0,
            "today_usd": format_money(revenue_on(today, "USD"), "USD") if show_billing else "",
            "today_khr": format_money(revenue_on(today, "KHR"), "KHR") if show_billing else "",
            "month_usd": format_money(revenue_in_month(today, "USD"), "USD") if show_billing else "",
            "month_khr": format_money(revenue_in_month(today, "KHR"), "KHR") if show_billing else "",
            "year_usd": format_money(revenue_in_year(today, "USD"), "USD") if show_billing else "",
            "year_khr": format_money(revenue_in_year(today, "KHR"), "KHR") if show_billing else "",
        },
        "course_bars": [
            {
                "course": course,
                "percent": int(course.student_count * 100 / max_count),
            }
            for course in course_bars_qs
        ],
        "unpaid_enrollments": unpaid_rows,
        "due_soon_enrollments": due_soon[:8] if show_billing else [],
        "overdue_enrollments": overdue[:8] if show_billing else [],
        "recent_payments": (
            Payment.objects.select_related("student", "course_class", "receipt")
            .filter(status=Payment.Status.COMPLETED)
            .order_by("-paid_on", "-created_at")[:6]
            if show_billing
            else []
        ),
        "recent_students": students.order_by("-created_at")[:6],
        "recent_enrollments": visible_enrollments(user)
        .select_related("student", "course_class")
        .order_by("-created_at")[:6],
        "attendance_today": _attendance_today(user, classes, today),
    }
    return render(request, "dashboard/index.html", context)
