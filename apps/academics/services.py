from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import log_event

from .models import CourseClass, Enrollment


def _today():
    return timezone.localdate()


def enroll_student(
    student,
    course_class,
    *,
    user=None,
    enrolled_on=None,
    note="",
    next_due_date=None,
    transferred_from=None,
):
    if not course_class.is_active:
        raise ValidationError("ថ្នាក់នេះមិនទាន់បើកទេ។")
    if Enrollment.objects.filter(
        student=student,
        course_class=course_class,
        status=Enrollment.Status.ACTIVE,
    ).exists():
        raise ValidationError("សិស្សនេះកំពុងរៀនក្នុងថ្នាក់នេះរួចហើយ។")

    enrollment = Enrollment.objects.create(
        student=student,
        course_class=course_class,
        status=Enrollment.Status.ACTIVE,
        enrolled_on=enrolled_on or _today(),
        next_due_date=next_due_date,
        note=note,
        transferred_from=transferred_from,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    log_event(
        action=AuditEvent.Action.ENROLLMENT_CREATED,
        summary=f"ចុះឈ្មោះ {student} ទៅ {course_class}",
        user=user,
        obj=enrollment,
    )
    return enrollment


def transfer_enrollment(enrollment, target_class, *, user=None, note=""):
    if enrollment.status != Enrollment.Status.ACTIVE:
        raise ValidationError("អាចផ្ទេរបានតែការចុះឈ្មោះដែលកំពុងរៀន។")
    if target_class.pk == enrollment.course_class_id:
        raise ValidationError("សូមជ្រើសថ្នាក់ថ្មី។")
    if not isinstance(target_class, CourseClass):
        raise ValidationError("ថ្នាក់គោលដៅមិនត្រឹមត្រូវ។")

    with transaction.atomic():
        enrollment.status = Enrollment.Status.TRANSFERRED
        enrollment.ended_on = _today()
        if note:
            enrollment.note = note
        enrollment.save(update_fields=["status", "ended_on", "note", "updated_at"])
        log_event(
            action=AuditEvent.Action.ENROLLMENT_TRANSFERRED,
            summary=f"ផ្ទេរ {enrollment.student} ពី {enrollment.course_class} ទៅ {target_class}",
            user=user,
            obj=enrollment,
        )
        return enroll_student(
            enrollment.student,
            target_class,
            user=user,
            note=note,
            transferred_from=enrollment,
        )


def set_enrollment_status(enrollment, status, *, user=None, note=""):
    allowed = {
        Enrollment.Status.SUSPENDED: {Enrollment.Status.ACTIVE},
        Enrollment.Status.ACTIVE: {Enrollment.Status.SUSPENDED},
        Enrollment.Status.DROPPED: {Enrollment.Status.ACTIVE, Enrollment.Status.SUSPENDED},
        Enrollment.Status.COMPLETED: {Enrollment.Status.ACTIVE},
    }
    permitted_from = allowed.get(status)
    if not permitted_from or enrollment.status not in permitted_from:
        raise ValidationError("មិនអាចប្ដូរស្ថានភាពនេះបានទេ។")

    enrollment.status = status
    if note:
        enrollment.note = note
    enrollment.ended_on = None if status in {Enrollment.Status.ACTIVE, Enrollment.Status.SUSPENDED} else _today()
    enrollment.save(update_fields=["status", "note", "ended_on", "updated_at"])
    log_event(
        action=AuditEvent.Action.ENROLLMENT_STATUS,
        summary=f"{enrollment.student} · {enrollment.get_status_display()}",
        user=user,
        obj=enrollment,
    )
    return enrollment
