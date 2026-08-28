from calendar import monthrange
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.core.constants import KHMER_MONTHS, WEEKDAY_LABELS

from .models import AttendanceRecord, Enrollment

VALID_STATUSES = {choice[0] for choice in AttendanceRecord.Status.choices}
STATUS_KEYS = [choice[0] for choice in AttendanceRecord.Status.choices]


def parse_attended_on(value, fallback):
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        return fallback


def parse_month(value, fallback):
    text = (value or "").strip()
    try:
        year_text, month_text = text.split("-", 1)
        return date(int(year_text), int(month_text), 1)
    except (TypeError, ValueError):
        return date(fallback.year, fallback.month, 1)


def add_months(month_start, delta):
    index = month_start.month - 1 + delta
    year = month_start.year + index // 12
    month = index % 12 + 1
    return date(year, month, 1)


def month_days(month_start):
    last = monthrange(month_start.year, month_start.month)[1]
    return [date(month_start.year, month_start.month, day) for day in range(1, last + 1)]


def month_label(month_start):
    return f"{KHMER_MONTHS[month_start.month]} {month_start.year}"


def weekday_short(when):
    return WEEKDAY_LABELS.get(when.weekday(), "")[:1]


def empty_status_counts():
    return {status: 0 for status in STATUS_KEYS}


def error_message(exc):
    if hasattr(exc, "messages") and exc.messages:
        return exc.messages[0]
    return str(exc)


def is_study_day(course_class, when):
    days = course_class.study_days or []
    try:
        weekday = when.weekday()
    except AttributeError:
        return False
    return weekday in {int(day) for day in days}


def roster_enrollments(course_class):
    return (
        Enrollment.objects.filter(
            course_class=course_class,
            status=Enrollment.Status.ACTIVE,
        )
        .select_related("student")
        .order_by("student__name_kh")
    )


def records_for_day(course_class, attended_on):
    return AttendanceRecord.objects.filter(course_class=course_class, attended_on=attended_on)


def sheet_rows(course_class, attended_on):
    existing = {row.enrollment_id: row for row in records_for_day(course_class, attended_on)}
    rows = []
    for enrollment in roster_enrollments(course_class):
        record = existing.get(enrollment.pk)
        rows.append(
            {
                "enrollment": enrollment,
                "student": enrollment.student,
                "status": record.status if record else "",
                "record": record,
            }
        )
    return rows


def day_counts(course_class, attended_on):
    counts = empty_status_counts()
    for row in records_for_day(course_class, attended_on).values("status").annotate(total=Count("id")):
        counts[row["status"]] = row["total"]
    counts["total"] = sum(counts[status] for status in STATUS_KEYS)
    return counts


def recent_days(course_class, limit=8):
    return list(
        AttendanceRecord.objects.filter(course_class=course_class)
        .values("attended_on")
        .annotate(
            total=Count("id"),
            present=Count("id", filter=Q(status=AttendanceRecord.Status.PRESENT)),
            late=Count("id", filter=Q(status=AttendanceRecord.Status.LATE)),
            absent=Count("id", filter=Q(status=AttendanceRecord.Status.ABSENT)),
            excused=Count("id", filter=Q(status=AttendanceRecord.Status.EXCUSED)),
        )
        .order_by("-attended_on")[:limit]
    )


def month_grid(course_class, month_start):
    days = month_days(month_start)
    by_enrollment = {}
    records = AttendanceRecord.objects.filter(
        course_class=course_class,
        attended_on__gte=days[0],
        attended_on__lte=days[-1],
    )
    for record in records:
        by_enrollment.setdefault(record.enrollment_id, {})[record.attended_on] = record.status

    rows = []
    totals = empty_status_counts()
    day_totals = {day: empty_status_counts() for day in days}
    for enrollment in roster_enrollments(course_class):
        marks = by_enrollment.get(enrollment.pk, {})
        summary = empty_status_counts()
        cells = []
        for day in days:
            status = marks.get(day, "")
            cells.append({"day": day, "status": status, "is_study_day": is_study_day(course_class, day)})
            if status in summary:
                summary[status] += 1
                totals[status] += 1
                day_totals[day][status] += 1
        summary["total"] = sum(summary[status] for status in STATUS_KEYS)
        rows.append(
            {
                "enrollment": enrollment,
                "student": enrollment.student,
                "cells": cells,
                "summary": summary,
            }
        )
    totals["total"] = sum(totals[status] for status in STATUS_KEYS)
    return {
        "days": [
            {"date": day, "is_study_day": is_study_day(course_class, day), "weekday": weekday_short(day)}
            for day in days
        ],
        "rows": rows,
        "totals": totals,
        "day_totals": [{"date": day, "counts": day_totals[day]} for day in days],
    }


def normalize_date_range(start, end):
    if start > end:
        start, end = end, start
    return start, end


def date_range_label(start, end):
    start, end = normalize_date_range(start, end)
    if start == end:
        return start.strftime("%d/%m/%Y")
    return f"{start.strftime('%d/%m/%Y')} – {end.strftime('%d/%m/%Y')}"


def parse_date_range(data, fallback):
    day = parse_attended_on(data.get("date") or data.get("attended_on"), fallback)
    start = parse_attended_on(data.get("from"), day)
    end = parse_attended_on(data.get("to"), start)
    return normalize_date_range(start, end)


def day_register(course_class, start, end):
    start, end = normalize_date_range(start, end)
    is_single_day = start == end
    range_counts = {}
    day_status = {}
    records = AttendanceRecord.objects.filter(
        course_class=course_class,
        attended_on__gte=start,
        attended_on__lte=end,
    )
    for record in records:
        counts = range_counts.setdefault(record.enrollment_id, empty_status_counts())
        if record.status in counts:
            counts[record.status] += 1
        if is_single_day and record.attended_on == start:
            day_status[record.enrollment_id] = record.status

    rows = []
    totals = empty_status_counts()
    for enrollment in roster_enrollments(course_class):
        summary = range_counts.get(enrollment.pk) or empty_status_counts()
        summary["total"] = sum(summary[status] for status in STATUS_KEYS)
        for status in STATUS_KEYS:
            totals[status] += summary[status]
        rows.append(
            {
                "enrollment": enrollment,
                "student": enrollment.student,
                "status": day_status.get(enrollment.pk, ""),
                "summary": summary,
            }
        )
    totals["total"] = sum(totals[status] for status in STATUS_KEYS)
    return {
        "rows": rows,
        "counts": totals,
        "is_study_day": is_study_day(course_class, start) if is_single_day else False,
        "is_single_day": is_single_day,
        "attended_on": start if is_single_day else None,
        "date_from": start,
        "date_to": end,
        "summary_label": date_range_label(start, end),
    }


def mark_class_attendance(course_class, attended_on, marks, *, user=None):
    roster = {enrollment.pk: enrollment for enrollment in roster_enrollments(course_class)}
    if not roster:
        raise ValidationError("ថ្នាក់នេះមិនទាន់មានសិស្សកំពុងរៀន។")
    cleaned = {}
    for enrollment_id, status in marks.items():
        try:
            enrollment_id = int(enrollment_id)
        except (TypeError, ValueError):
            continue
        if enrollment_id not in roster:
            continue
        if status not in VALID_STATUSES:
            raise ValidationError("ស្ថានភាពវត្តមានមិនត្រឹមត្រូវ។")
        cleaned[enrollment_id] = status
    if not cleaned:
        raise ValidationError("សូមចុះវត្តមានសិស្សយ៉ាងតិចម្នាក់។")

    marked_by = user if getattr(user, "is_authenticated", False) else None
    with transaction.atomic():
        for enrollment_id, status in cleaned.items():
            enrollment = roster[enrollment_id]
            AttendanceRecord.objects.update_or_create(
                enrollment=enrollment,
                attended_on=attended_on,
                defaults={
                    "course_class": course_class,
                    "student": enrollment.student,
                    "status": status,
                    "marked_by": marked_by,
                },
            )
        log_event(
            action=AuditEvent.Action.ATTENDANCE_MARKED,
            summary=f"ចុះវត្តមាន {course_class.name} · {attended_on.strftime('%d/%m/%Y')} · {len(cleaned)} នាក់",
            user=user,
            obj=course_class,
            extra={"date": attended_on.isoformat(), "count": len(cleaned)},
        )
    return len(cleaned)


def mark_month_attendance(course_class, marks, *, user=None):
    roster = {enrollment.pk: enrollment for enrollment in roster_enrollments(course_class)}
    if not roster:
        raise ValidationError("ថ្នាក់នេះមិនទាន់មានសិស្សកំពុងរៀន។")
    cleaned = []
    for (enrollment_id, attended_on), status in marks.items():
        try:
            enrollment_id = int(enrollment_id)
        except (TypeError, ValueError):
            continue
        if enrollment_id not in roster or not status:
            continue
        if status not in VALID_STATUSES:
            raise ValidationError("ស្ថានភាពវត្តមានមិនត្រឹមត្រូវ។")
        cleaned.append((enrollment_id, attended_on, status))
    if not cleaned:
        raise ValidationError("សូមចុះវត្តមានសិស្សយ៉ាងតិចម្នាក់។")

    marked_by = user if getattr(user, "is_authenticated", False) else None
    with transaction.atomic():
        for enrollment_id, attended_on, status in cleaned:
            enrollment = roster[enrollment_id]
            AttendanceRecord.objects.update_or_create(
                enrollment=enrollment,
                attended_on=attended_on,
                defaults={
                    "course_class": course_class,
                    "student": enrollment.student,
                    "status": status,
                    "marked_by": marked_by,
                },
            )
        log_event(
            action=AuditEvent.Action.ATTENDANCE_MARKED,
            summary=f"ចុះវត្តមាន {course_class.name} · {len(cleaned)} កំណត់ត្រា",
            user=user,
            obj=course_class,
            extra={"count": len(cleaned)},
        )
    return len(cleaned)


def attendance_report_rows(filters, classes):
    start = filters.get("date_from")
    end = filters.get("date_to")
    qs = AttendanceRecord.objects.filter(course_class__in=classes).select_related(
        "student",
        "course_class",
    )
    if start:
        qs = qs.filter(attended_on__gte=start)
    if end:
        qs = qs.filter(attended_on__lte=end)
    course = filters.get("course")
    if course:
        qs = qs.filter(course_class__course=course)
    course_class = filters.get("course_class")
    if course_class:
        qs = qs.filter(course_class=course_class)

    grouped = {}
    for record in qs:
        key = (record.student_id, record.course_class_id)
        item = grouped.get(key)
        if not item:
            item = {
                "student": record.student,
                "course_class": record.course_class,
                "present": 0,
                "late": 0,
                "absent": 0,
                "excused": 0,
            }
            grouped[key] = item
        item[record.status] = item.get(record.status, 0) + 1

    rows = []
    for item in grouped.values():
        total = item["present"] + item["late"] + item["absent"] + item["excused"]
        item["total"] = total
        attended = item["present"] + item["late"]
        item["rate"] = f"{round(attended * 100 / total)}%" if total else "—"
        rows.append(item)
    rows.sort(key=lambda row: (row["course_class"].name, row["student"].name_kh))
    return rows


def student_attendance_history(student, classes, limit=40):
    return list(
        AttendanceRecord.objects.filter(student=student, course_class__in=classes)
        .select_related("course_class")
        .order_by("-attended_on", "-pk")[:limit]
    )


def student_attendance_counts(student, classes):
    counts = empty_status_counts()
    for row in (
        AttendanceRecord.objects.filter(student=student, course_class__in=classes)
        .values("status")
        .annotate(total=Count("id"))
    ):
        counts[row["status"]] = row["total"]
    counts["total"] = sum(counts[status] for status in STATUS_KEYS)
    return counts
