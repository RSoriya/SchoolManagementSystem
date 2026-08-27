from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.utils import timezone

from apps.billing.models import Payment, Refund
from apps.billing.services import due_soon_enrollments, overdue_enrollments, unpaid_enrollments
from apps.core.constants import format_money

ZERO = Decimal("0.00")
COUNTED_STATUSES = (Payment.Status.COMPLETED, Payment.Status.REFUNDED)


def default_range(today=None):
    today = today or timezone.localdate()
    return today.replace(day=1), today


def year_range(today=None):
    today = today or timezone.localdate()
    return date(today.year, 1, 1), date(today.year, 12, 31)


def _money():
    return {"USD": ZERO, "KHR": ZERO}


def _add(bucket, currency, amount):
    bucket[currency] = bucket.get(currency, ZERO) + (amount or ZERO)


def _display(bucket):
    return {
        "usd": format_money(bucket.get("USD", ZERO), "USD"),
        "khr": format_money(bucket.get("KHR", ZERO), "KHR"),
        "usd_amount": bucket.get("USD", ZERO),
        "khr_amount": bucket.get("KHR", ZERO),
    }


def apply_common_filters(queryset, filters, *, date_field="paid_on"):
    start = filters.get("date_from")
    end = filters.get("date_to")
    if start:
        queryset = queryset.filter(**{f"{date_field}__gte": start})
    if end:
        queryset = queryset.filter(**{f"{date_field}__lte": end})
    course = filters.get("course")
    if course:
        queryset = queryset.filter(course_class__course=course)
    course_class = filters.get("course_class")
    if course_class:
        queryset = queryset.filter(course_class=course_class)
    currency = filters.get("currency")
    if currency:
        queryset = queryset.filter(currency=currency)
    method = filters.get("method")
    if method:
        queryset = queryset.filter(method=method)
    status = filters.get("status")
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def filtered_payments(filters):
    return apply_common_filters(
        Payment.objects.select_related(
            "student",
            "course_class__course",
            "method",
            "receipt",
        ),
        filters,
    ).order_by("-paid_on", "-created_at")


def filtered_refunds(filters):
    qs = Refund.objects.select_related(
        "payment__student",
        "payment__course_class__course",
        "method",
    )
    start = filters.get("date_from")
    end = filters.get("date_to")
    if start:
        qs = qs.filter(refunded_on__gte=start)
    if end:
        qs = qs.filter(refunded_on__lte=end)
    course = filters.get("course")
    if course:
        qs = qs.filter(payment__course_class__course=course)
    course_class = filters.get("course_class")
    if course_class:
        qs = qs.filter(payment__course_class=course_class)
    currency = filters.get("currency")
    if currency:
        qs = qs.filter(currency=currency)
    method = filters.get("method")
    if method:
        qs = qs.filter(method=method)
    return qs.order_by("-refunded_on", "-created_at")


def _filter_enrollments(queryset, filters):
    course = filters.get("course")
    if course:
        queryset = queryset.filter(course_class__course=course)
    course_class = filters.get("course_class")
    if course_class:
        queryset = queryset.filter(course_class=course_class)
    return queryset


def unpaid_rows(filters, today=None):
    return _filter_enrollments(unpaid_enrollments(today), filters)


def overdue_rows(filters, today=None):
    return _filter_enrollments(overdue_enrollments(today), filters)


def paid_groups(filters):
    payments = filtered_payments({**filters, "status": Payment.Status.COMPLETED})
    groups = {}
    for payment in payments:
        key = (payment.student_id, payment.course_class_id)
        item = groups.get(key)
        if not item:
            item = {
                "student": payment.student,
                "course_class": payment.course_class,
                "last_paid_on": payment.paid_on,
                "count": 0,
                "totals": _money(),
            }
            groups[key] = item
        item["count"] += 1
        _add(item["totals"], payment.currency, payment.total_amount)
        if payment.paid_on > item["last_paid_on"]:
            item["last_paid_on"] = payment.paid_on
    rows = sorted(groups.values(), key=lambda row: row["student"].name_kh)
    for row in rows:
        row["totals_display"] = _display(row["totals"])
    return rows


def revenue_summary(filters):
    payments = filtered_payments(filters)
    counted = payments.filter(status__in=COUNTED_STATUSES)
    refunds = filtered_refunds(filters)
    inflow = _money()
    outflow = _money()
    discount = _money()
    scholarship = _money()
    late_fee = _money()
    by_course = defaultdict(lambda: {"inflow": _money(), "outflow": _money(), "label": ""})
    by_class = defaultdict(lambda: {"inflow": _money(), "outflow": _money(), "label": ""})

    for payment in counted:
        _add(inflow, payment.currency, payment.total_amount)
        _add(discount, payment.currency, payment.discount_amount)
        _add(scholarship, payment.currency, payment.scholarship_amount)
        _add(late_fee, payment.currency, payment.late_fee)
        course_key = payment.course_class.course_id
        class_key = payment.course_class_id
        by_course[course_key]["label"] = str(payment.course_class.course)
        _add(by_course[course_key]["inflow"], payment.currency, payment.total_amount)
        by_class[class_key]["label"] = payment.course_class.name
        _add(by_class[class_key]["inflow"], payment.currency, payment.total_amount)

    for refund in refunds:
        _add(outflow, refund.currency, refund.amount)
        payment = refund.payment
        course_key = payment.course_class.course_id
        class_key = payment.course_class_id
        by_course[course_key]["label"] = str(payment.course_class.course)
        _add(by_course[course_key]["outflow"], refund.currency, refund.amount)
        by_class[class_key]["label"] = payment.course_class.name
        _add(by_class[class_key]["outflow"], refund.currency, refund.amount)

    net = {
        "USD": inflow.get("USD", ZERO) - outflow.get("USD", ZERO),
        "KHR": inflow.get("KHR", ZERO) - outflow.get("KHR", ZERO),
    }

    def _breakdown(mapping):
        rows = []
        for item in mapping.values():
            net_usd = item["inflow"].get("USD", ZERO) - item["outflow"].get("USD", ZERO)
            net_khr = item["inflow"].get("KHR", ZERO) - item["outflow"].get("KHR", ZERO)
            rows.append(
                {
                    "label": item["label"],
                    "usd": format_money(net_usd, "USD"),
                    "khr": format_money(net_khr, "KHR"),
                    "usd_amount": net_usd,
                    "khr_amount": net_khr,
                }
            )
        return sorted(rows, key=lambda row: row["label"])

    return {
        "net": _display(net),
        "inflow": _display(inflow),
        "refunds": _display(outflow),
        "discount": _display(discount),
        "scholarship": _display(scholarship),
        "late_fee": _display(late_fee),
        "by_course": _breakdown(by_course),
        "by_class": _breakdown(by_class),
        "payment_count": payments.count(),
        "counted_count": counted.count(),
        "refund_count": refunds.count(),
    }


def hub_stats(today=None):
    today = today or timezone.localdate()
    month_start, month_end = default_range(today)
    year_start, year_end = year_range(today)
    month_filters = {"date_from": month_start, "date_to": month_end}
    year_filters = {"date_from": year_start, "date_to": year_end}
    day_filters = {"date_from": today, "date_to": today}
    month_summary = revenue_summary(month_filters)
    return {
        "today": revenue_summary(day_filters),
        "month": month_summary,
        "year": revenue_summary(year_filters),
        "unpaid": unpaid_enrollments(today).values("student_id").distinct().count(),
        "overdue": overdue_enrollments(today).values("student_id").distinct().count(),
        "due_soon": due_soon_enrollments(today).values("student_id").distinct().count(),
        "paid_month": len(paid_groups(month_filters)),
        "refunds_month": filtered_refunds(month_filters).count(),
    }
