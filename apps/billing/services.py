from collections import defaultdict
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.academics.models import Course, Enrollment
from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.core.constants import KHMER_MONTHS, format_money
from apps.core.services import allocate_receipt_number, get_school_settings

from .models import Payment, Receipt, Refund

ZERO = Decimal("0.00")
PAYABLE_STATUSES = (Enrollment.Status.ACTIVE, Enrollment.Status.SUSPENDED)


def _quantize(amount):
    return (amount or ZERO).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def month_bounds(when=None):
    when = when or timezone.localdate()
    start = when.replace(day=1)
    end = when.replace(day=monthrange(when.year, when.month)[1])
    label = f"{KHMER_MONTHS[when.month]} {when.year}"
    return start, end, label


def add_calendar_month(when, months=1):
    """Advance a date by calendar months, clamping the day (31 Jan → 28/29 Feb)."""
    month_index = when.month - 1 + months
    year = when.year + month_index // 12
    month = month_index % 12 + 1
    day = min(when.day, monthrange(year, month)[1])
    return date(year, month, day)


def monthly_schedule(enrollment, paid_on=None):
    """Period covered by this payment, and the suggested next due date."""
    paid_on = paid_on or timezone.localdate()
    anchor = enrollment.next_due_date or paid_on
    start, end, label = month_bounds(anchor)
    return {
        "period_start": start,
        "period_end": end,
        "period_label": label,
        "next_due_date": add_calendar_month(anchor, 1),
    }


def compute_payment_total(tuition, registration_fee, late_fee, discount, scholarship):
    tuition = _quantize(tuition)
    registration_fee = _quantize(registration_fee)
    late_fee = _quantize(late_fee)
    discount = _quantize(discount)
    scholarship = _quantize(scholarship)
    if min(tuition, registration_fee, late_fee, discount, scholarship) < 0:
        raise ValidationError("ចំនួនទឹកប្រាក់មិនអាចតូចជាង 0 បានទេ។")
    gross = tuition + registration_fee + late_fee
    reductions = discount + scholarship
    if reductions > gross:
        raise ValidationError("បញ្ចុះតម្លៃ និងអាហារូបករមិនអាចលើសថ្លៃសរុបបានទេ។")
    total = gross - reductions
    if total <= 0:
        raise ValidationError("ចំនួនបង់សរុបត្រូវធំជាង 0។")
    return total


def billing_period(enrollment, paid_on=None):
    """The open billing period for this enrollment."""
    course = enrollment.course_class.course
    if course.fee_type == Course.FeeType.MONTHLY:
        return monthly_schedule(enrollment, paid_on)
    return {
        "period_start": enrollment.course_class.start_date,
        "period_end": enrollment.course_class.end_date,
        "period_label": course.get_fee_type_display(),
        "next_due_date": None,
    }


def period_tuition_paid(enrollment, period_start):
    qs = Payment.objects.filter(
        enrollment_id=enrollment.pk,
        status=Payment.Status.COMPLETED,
    )
    if enrollment.course_class.course.fee_type == Course.FeeType.MONTHLY:
        if period_start is None:
            qs = qs.filter(period_start__isnull=True)
        else:
            qs = qs.filter(period_start=period_start)
    return qs.aggregate(total=Sum("tuition_amount"))["total"] or ZERO


def period_balance(enrollment, *, paid_on=None, period_start=None):
    course = enrollment.course_class.course
    period = billing_period(enrollment, paid_on)
    if period_start is None:
        period_start = period["period_start"]
        period_end = period["period_end"]
        period_label = period["period_label"]
    elif period_start == period["period_start"]:
        period_end = period["period_end"]
        period_label = period["period_label"]
    elif period_start:
        _start, period_end, period_label = month_bounds(period_start)
    else:
        period_end = period["period_end"]
        period_label = period["period_label"]
    fee = _quantize(course.default_fee)
    paid = _quantize(period_tuition_paid(enrollment, period_start))
    remaining = fee - paid
    if remaining < ZERO:
        remaining = ZERO
    return {
        "fee": fee,
        "paid": paid,
        "remaining": remaining,
        "period_start": period_start,
        "period_end": period_end,
        "period_label": period_label,
        "currency": course.currency,
    }


def attach_period_balances(enrollments, today=None):
    rows = list(enrollments)
    if not rows:
        return rows
    ids = [row.pk for row in rows]
    paid_map = defaultdict(lambda: ZERO)
    payments = Payment.objects.filter(
        enrollment_id__in=ids,
        status=Payment.Status.COMPLETED,
    ).values("enrollment_id", "period_start", "tuition_amount")
    fee_types = {row.pk: row.course_class.course.fee_type for row in rows}
    for payment in payments:
        key_period = (
            payment["period_start"]
            if fee_types.get(payment["enrollment_id"]) == Course.FeeType.MONTHLY
            else None
        )
        paid_map[(payment["enrollment_id"], key_period)] += payment["tuition_amount"] or ZERO
    for enrollment in rows:
        period = billing_period(enrollment, today)
        course = enrollment.course_class.course
        fee = _quantize(course.default_fee)
        key_period = period["period_start"] if course.fee_type == Course.FeeType.MONTHLY else None
        paid = _quantize(paid_map.get((enrollment.pk, key_period), ZERO))
        remaining = fee - paid
        if remaining < ZERO:
            remaining = ZERO
        enrollment.period_fee = fee
        enrollment.period_paid = paid
        enrollment.period_remaining = remaining
        enrollment.period_fee_display = format_money(fee, course.currency)
        enrollment.period_paid_display = format_money(paid, course.currency)
        enrollment.period_remaining_display = format_money(remaining, course.currency)
    return rows


def _limit_to_outstanding(queryset, today=None):
    outstanding_ids = [
        row.pk for row in attach_period_balances(queryset, today) if row.period_remaining > 0
    ]
    return queryset.filter(pk__in=outstanding_ids)


def payable_enrollments():
    return (
        Enrollment.objects.filter(status__in=PAYABLE_STATUSES)
        .select_related("student", "course_class__course")
        .order_by("student__name_kh", "course_class__name")
    )


def unpaid_enrollments(today=None):
    today = today or timezone.localdate()
    return _limit_to_outstanding(
        Enrollment.objects.filter(status=Enrollment.Status.ACTIVE)
        .filter(Q(next_due_date__isnull=True) | Q(next_due_date__lte=today))
        .select_related("student", "course_class__course")
        .order_by("next_due_date", "student__name_kh"),
        today,
    )


def overdue_enrollments(today=None):
    today = today or timezone.localdate()
    return _limit_to_outstanding(
        Enrollment.objects.filter(
            status=Enrollment.Status.ACTIVE,
            next_due_date__lt=today,
        ).select_related("student", "course_class__course"),
        today,
    )


def due_soon_enrollments(today=None, days=None):
    today = today or timezone.localdate()
    if days is None:
        days = get_school_settings().reminder_days_before_due or 3
    target = today + timedelta(days=int(days))
    return _limit_to_outstanding(
        Enrollment.objects.filter(
            status=Enrollment.Status.ACTIVE,
            next_due_date=target,
        ).select_related("student", "course_class__course"),
        today,
    )


def completed_payments():
    return Payment.objects.filter(status=Payment.Status.COMPLETED)


def _sum_amount(queryset, field="total_amount"):
    return queryset.aggregate(total=Sum(field))["total"] or ZERO


def revenue_in_range(start, end, currency):
    inflow = _sum_amount(
        Payment.objects.filter(
            paid_on__gte=start,
            paid_on__lte=end,
            currency=currency,
            status__in=[Payment.Status.COMPLETED, Payment.Status.REFUNDED],
        )
    )
    outflow = _sum_amount(
        Refund.objects.filter(
            refunded_on__gte=start,
            refunded_on__lte=end,
            currency=currency,
        ),
        "amount",
    )
    return inflow - outflow


def revenue_on(day, currency):
    return revenue_in_range(day, day, currency)


def revenue_in_month(day, currency):
    start, end, _label = month_bounds(day)
    return revenue_in_range(start, end, currency)


def revenue_in_year(day, currency):
    start = date(day.year, 1, 1)
    end = date(day.year, 12, 31)
    return revenue_in_range(start, end, currency)


def _admin_display_name(user):
    if not user:
        return ""
    return (
        getattr(user, "full_name_kh", "")
        or user.get_full_name()
        or user.username
    )


def _restore_due_date_if_latest(payment):
    later_exists = (
        Payment.objects.filter(
            enrollment_id=payment.enrollment_id,
            status=Payment.Status.COMPLETED,
            created_at__gt=payment.created_at,
        )
        .exclude(pk=payment.pk)
        .exists()
    )
    if not later_exists:
        enrollment = payment.enrollment
        enrollment.next_due_date = payment.previous_due_date
        enrollment.save(update_fields=["next_due_date", "updated_at"])


def collect_payment(
    *,
    enrollment,
    paid_on,
    tuition_amount,
    method,
    registration_fee=ZERO,
    late_fee=ZERO,
    discount_amount=ZERO,
    scholarship_amount=ZERO,
    transaction_reference="",
    period_start=None,
    period_end=None,
    period_label="",
    next_due_date=None,
    note="",
    user=None,
):
    if enrollment.status not in PAYABLE_STATUSES:
        raise ValidationError("អាចទទួលបង់បានតែសិស្សដែលកំពុងរៀន ឬផ្អាក។")
    if not method.is_active:
        raise ValidationError("វិធីបង់ប្រាក់នេះមិនទាន់បើកទេ។")
    if method.requires_reference and not (transaction_reference or "").strip():
        raise ValidationError("សូមបំពេញលេខយោងប្រតិបត្តិការ។")
    if not method.requires_reference:
        transaction_reference = ""

    total = compute_payment_total(
        tuition_amount,
        registration_fee,
        late_fee,
        discount_amount,
        scholarship_amount,
    )

    school = get_school_settings()
    with transaction.atomic():
        enrollment = (
            Enrollment.objects.select_for_update()
            .select_related("student", "course_class__course")
            .get(pk=enrollment.pk)
        )
        course = enrollment.course_class.course
        if course.fee_type == Course.FeeType.MONTHLY:
            suggestion = monthly_schedule(enrollment, paid_on)
            period_start = period_start or suggestion["period_start"]
            period_end = period_end or suggestion["period_end"]
            period_label = period_label or suggestion["period_label"]
        else:
            period_start = period_start or enrollment.course_class.start_date
            period_end = period_end or enrollment.course_class.end_date
            period_label = period_label or course.get_fee_type_display()

        balance = period_balance(enrollment, paid_on=paid_on, period_start=period_start)
        tuition = _quantize(tuition_amount)
        if tuition > balance["remaining"]:
            raise ValidationError(
                f"ថ្លៃសិក្សាលើសចំនួននៅជំពាក់ ({format_money(balance['remaining'], course.currency)})។"
            )
        remaining_after = _quantize(balance["remaining"] - tuition)
        if remaining_after > ZERO:
            next_due_date = enrollment.next_due_date
        elif course.fee_type == Course.FeeType.MONTHLY:
            next_due_date = next_due_date or monthly_schedule(enrollment, paid_on)["next_due_date"]

        payment = Payment.objects.create(
            enrollment=enrollment,
            student=enrollment.student,
            course_class=enrollment.course_class,
            paid_on=paid_on,
            currency=course.currency,
            tuition_amount=_quantize(tuition_amount),
            registration_fee=_quantize(registration_fee),
            late_fee=_quantize(late_fee),
            discount_amount=_quantize(discount_amount),
            scholarship_amount=_quantize(scholarship_amount),
            total_amount=total,
            fee_amount=balance["fee"],
            balance_after=remaining_after,
            method=method,
            transaction_reference=(transaction_reference or "").strip(),
            period_type=course.fee_type,
            period_label=period_label or "",
            period_start=period_start,
            period_end=period_end,
            previous_due_date=enrollment.next_due_date,
            next_due_date=next_due_date,
            note=note or "",
            status=Payment.Status.COMPLETED,
            created_by=user if getattr(user, "is_authenticated", False) else None,
        )
        Receipt.objects.create(
            payment=payment,
            receipt_number=allocate_receipt_number(when=paid_on),
            issued_by=user if getattr(user, "is_authenticated", False) else None,
            status=Receipt.Status.ISSUED,
            school_name=school.school_name,
            school_address=school.address,
            school_phone=school.phone,
            student_id_snapshot=enrollment.student.student_id,
            student_name_kh=enrollment.student.name_kh,
            student_name_en=enrollment.student.name_en,
            course_name=course.name_kh or course.name,
            class_name=enrollment.course_class.name,
            issued_by_name=_admin_display_name(user),
        )
        enrollment.next_due_date = next_due_date
        enrollment.save(update_fields=["next_due_date", "updated_at"])
        remaining_note = (
            f" · នៅជំពាក់ {format_money(remaining_after, course.currency)}"
            if remaining_after > ZERO
            else ""
        )
        log_event(
            action=AuditEvent.Action.PAYMENT_COLLECTED,
            summary=f"ទទួលបង់ {payment.total_display}{remaining_note} · {enrollment.student}",
            user=user,
            obj=payment,
        )
    return payment


def void_payment(payment, *, user=None, reason=""):
    if payment.status == Payment.Status.VOIDED:
        raise ValidationError("ការបង់នេះត្រូវបានលុបចោលរួចហើយ។")
    if payment.status == Payment.Status.REFUNDED:
        raise ValidationError("ការបង់ដែលបានសងប្រាក់មិនអាចលុបចោលបានទេ។")

    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update(of=("self",))
            .select_related("enrollment", "receipt")
            .get(pk=payment.pk)
        )
        if payment.status != Payment.Status.COMPLETED:
            raise ValidationError("អាចលុបចោលបានតែការបង់ដែលបានបង់។")
        payment.status = Payment.Status.VOIDED
        payment.voided_at = timezone.now()
        payment.voided_by = user if getattr(user, "is_authenticated", False) else None
        payment.void_reason = reason or ""
        payment.save(update_fields=["status", "voided_at", "voided_by", "void_reason", "updated_at"])

        receipt = payment.receipt
        receipt.status = Receipt.Status.VOIDED
        receipt.save(update_fields=["status"])
        _restore_due_date_if_latest(payment)
        log_event(
            action=AuditEvent.Action.PAYMENT_VOIDED,
            summary=f"លុបចោលការបង់ {payment.total_display} · {payment.student}",
            user=user,
            obj=payment,
            extra={"reason": reason or ""},
        )
    return payment


def refund_payment(payment, *, method, reason, refunded_on=None, user=None):
    if payment.status == Payment.Status.VOIDED:
        raise ValidationError("ការបង់ដែលបានលុបចោលមិនអាចសងបានទេ។")
    if payment.status == Payment.Status.REFUNDED:
        raise ValidationError("ការបង់នេះត្រូវបានសងរួចហើយ។")
    if payment.status != Payment.Status.COMPLETED:
        raise ValidationError("អាចសងបានតែការបង់ពេញ។")
    if not (reason or "").strip():
        raise ValidationError("សូមបំពេញមូលហេតុសងប្រាក់។")
    if not method:
        raise ValidationError("សូមជ្រើសវិធីសងប្រាក់។")

    refunded_on = refunded_on or timezone.localdate()
    with transaction.atomic():
        payment = Payment.objects.select_for_update(of=("self",)).select_related("enrollment", "student").get(pk=payment.pk)
        if payment.status != Payment.Status.COMPLETED:
            raise ValidationError("ការបង់នេះត្រូវបានសង ឬលុបចោលរួចហើយ។")
        refund = Refund.objects.create(
            payment=payment,
            refunded_on=refunded_on,
            amount=payment.total_amount,
            currency=payment.currency,
            method=method,
            reason=reason.strip(),
            created_by=user if getattr(user, "is_authenticated", False) else None,
        )
        payment.status = Payment.Status.REFUNDED
        payment.save(update_fields=["status", "updated_at"])
        _restore_due_date_if_latest(payment)
        log_event(
            action=AuditEvent.Action.PAYMENT_REFUNDED,
            summary=f"សង {payment.total_display} · {payment.student}",
            user=user,
            obj=refund,
            extra={"reason": reason.strip()},
        )
    return refund


def enrollment_payload(enrollment, today=None):
    today = today or timezone.localdate()
    course = enrollment.course_class.course
    balance = period_balance(enrollment, paid_on=today)
    if course.fee_type == Course.FeeType.MONTHLY:
        suggestion = monthly_schedule(enrollment, today)
        start = suggestion["period_start"]
        end = suggestion["period_end"]
        label = suggestion["period_label"]
        next_due = suggestion["next_due_date"]
    else:
        start = balance["period_start"]
        end = balance["period_end"]
        label = balance["period_label"]
        next_due = None
    return {
        "id": enrollment.pk,
        "currency": course.currency,
        "fee": str(balance["fee"]),
        "paid": str(balance["paid"]),
        "remaining": str(balance["remaining"]),
        "fee_type": course.fee_type,
        "due": enrollment.next_due_date.isoformat() if enrollment.next_due_date else "",
        "next_due": next_due.isoformat() if next_due else "",
        "period_start": start.isoformat() if start else "",
        "period_end": end.isoformat() if end else "",
        "period_label": label,
        "student": enrollment.student.display_name,
        "student_id": enrollment.student.student_id,
        "course": course.name,
        "class_name": enrollment.course_class.name,
        "money": format_money(balance["fee"], course.currency),
        "money_paid": format_money(balance["paid"], course.currency),
        "money_remaining": format_money(balance["remaining"], course.currency),
    }
