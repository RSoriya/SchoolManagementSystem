from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.accounts.permissions import admin_required
from apps.core.constants import format_money
from apps.core.pagination import extra_query, paginate, per_page_value

_paginate = paginate
from apps.core.services import get_school_settings

from .exporters import excel_response, pdf_response
from .forms import REPORT_KINDS, SNAPSHOT_KINDS, ReportFilterForm
from .services import (
    default_range,
    filtered_payments,
    filtered_refunds,
    hub_stats,
    overdue_rows,
    paid_groups,
    revenue_summary,
    unpaid_rows,
    year_range,
)


def _export_query(request):
    params = request.GET.copy()
    params.pop("page", None)
    params.pop("print", None)
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else ""


def _filters_from_form(form, kind, today):
    if not form.is_valid():
        data = {}
    else:
        data = {key: value for key, value in form.cleaned_data.items() if value not in (None, "")}
    if kind not in SNAPSHOT_KINDS:
        if "date_from" not in data and "date_to" not in data:
            start, end = default_range(today)
            data.setdefault("date_from", start)
            data.setdefault("date_to", end)
            if not form.is_bound:
                form.initial["date_from"] = start
                form.initial["date_to"] = end
    return data


def _period_label(filters, kind, today):
    if kind in SNAPSHOT_KINDS:
        return f"ស្ថានភាពថ្ងៃ {today.strftime('%d/%m/%Y')}"
    start = filters.get("date_from")
    end = filters.get("date_to")
    if start and end:
        return f"{start.strftime('%d/%m/%Y')} – {end.strftime('%d/%m/%Y')}"
    if start:
        return f"ពី {start.strftime('%d/%m/%Y')}"
    if end:
        return f"ដល់ {end.strftime('%d/%m/%Y')}"
    return "គ្រប់រយៈពេល"


def _build_report(kind, filters, today):
    summary = revenue_summary(filters) if kind in {"revenue", "paid", "refunds"} else None
    if kind == "revenue":
        rows = list(filtered_payments(filters))
        headers = ["ល.រ", "ថ្ងៃបង់", "សិស្ស", "លេខសម្គាល់", "ថ្នាក់", "វិធីបង់", "ស្ថានភាព", "សរុប"]
        table = [
            [
                index,
                payment.paid_on.strftime("%d/%m/%Y"),
                payment.student.name_kh,
                payment.student.student_id,
                payment.course_class.name,
                payment.method.name,
                payment.get_status_display(),
                payment.total_display,
            ]
            for index, payment in enumerate(rows, start=1)
        ]
        kpis = [
            ("ចំណូលសុទ្ធ USD", summary["net"]["usd"]),
            ("ចំណូលសុទ្ធ KHR", summary["net"]["khr"]),
            ("បញ្ចុះតម្លៃ", f"{summary['discount']['usd']} · {summary['discount']['khr']}"),
            ("អាហារូបករ", f"{summary['scholarship']['usd']} · {summary['scholarship']['khr']}"),
            ("សងប្រាក់", f"{summary['refunds']['usd']} · {summary['refunds']['khr']}"),
        ]
    elif kind == "paid":
        rows = paid_groups(filters)
        headers = ["ល.រ", "សិស្ស", "លេខសម្គាល់", "ថ្នាក់", "ចុងក្រោយបង់", "ចំនួនដង", "USD", "KHR"]
        table = [
            [
                index,
                row["student"].name_kh,
                row["student"].student_id,
                row["course_class"].name,
                row["last_paid_on"].strftime("%d/%m/%Y"),
                row["count"],
                row["totals_display"]["usd"],
                row["totals_display"]["khr"],
            ]
            for index, row in enumerate(rows, start=1)
        ]
        usd_total = sum((row["totals"].get("USD") or 0) for row in rows)
        khr_total = sum((row["totals"].get("KHR") or 0) for row in rows)
        kpis = [
            ("សិស្ស/ថ្នាក់បានបង់", str(len(rows))),
            ("បានបង់ USD", format_money(usd_total, "USD")),
            ("បានបង់ KHR", format_money(khr_total, "KHR")),
        ]
    elif kind == "unpaid":
        rows = list(unpaid_rows(filters, today))
        headers = ["ល.រ", "សិស្ស", "លេខសម្គាល់", "ថ្នាក់", "Due Date", "ថ្លៃវគ្គ"]
        table = [
            [
                index,
                enrollment.student.name_kh,
                enrollment.student.student_id,
                enrollment.course_class.name,
                enrollment.next_due_date.strftime("%d/%m/%Y") if enrollment.next_due_date else "មិនទាន់កំណត់",
                format_money(enrollment.course_class.course.default_fee, enrollment.course_class.course.currency),
            ]
            for index, enrollment in enumerate(rows, start=1)
        ]
        kpis = [("សិស្សមិនទាន់បង់", str(len({row.student_id for row in rows})))]
    elif kind == "overdue":
        rows = list(overdue_rows(filters, today))
        headers = ["ល.រ", "សិស្ស", "លេខសម្គាល់", "ថ្នាក់", "Due Date", "ថ្លៃវគ្គ"]
        table = [
            [
                index,
                enrollment.student.name_kh,
                enrollment.student.student_id,
                enrollment.course_class.name,
                enrollment.next_due_date.strftime("%d/%m/%Y"),
                format_money(enrollment.course_class.course.default_fee, enrollment.course_class.course.currency),
            ]
            for index, enrollment in enumerate(rows, start=1)
        ]
        kpis = [("សិស្សហួស Due Date", str(len({row.student_id for row in rows})))]
    elif kind == "refunds":
        rows = list(filtered_refunds(filters))
        headers = ["ល.រ", "ថ្ងៃសង", "សិស្ស", "លេខសម្គាល់", "ថ្នាក់", "វិធីសង", "មូលហេតុ", "ចំនួន"]
        table = [
            [
                index,
                refund.refunded_on.strftime("%d/%m/%Y"),
                refund.payment.student.name_kh,
                refund.payment.student.student_id,
                refund.payment.course_class.name,
                refund.method.name,
                refund.reason,
                format_money(refund.amount, refund.currency),
            ]
            for index, refund in enumerate(rows, start=1)
        ]
        kpis = [
            ("ចំនួនសង", str(len(rows))),
            ("សង USD", summary["refunds"]["usd"]),
            ("សង KHR", summary["refunds"]["khr"]),
        ]
    else:
        raise Http404()
    return {
        "kind": kind,
        "title": REPORT_KINDS[kind],
        "headers": headers,
        "table": table,
        "rows": rows,
        "kpis": kpis,
        "summary": summary,
    }


@admin_required
@require_GET
def index(request):
    today = timezone.localdate()
    month_start, month_end = default_range(today)
    year_start, year_end = year_range(today)
    stats = hub_stats(today)
    return render(
        request,
        "reports/index.html",
        {
            "page_title": "របាយការណ៍",
            "today": today,
            "stats": stats,
            "month_query": f"?date_from={month_start.isoformat()}&date_to={month_end.isoformat()}",
            "year_query": f"?date_from={year_start.isoformat()}&date_to={year_end.isoformat()}",
            "today_query": f"?date_from={today.isoformat()}&date_to={today.isoformat()}",
        },
    )


def _report_context(request, kind):
    if kind not in REPORT_KINDS:
        raise Http404()
    today = timezone.localdate()
    start, end = default_range(today)
    initial = {}
    if kind not in SNAPSHOT_KINDS:
        initial = {"date_from": start, "date_to": end}
    form = ReportFilterForm(request.GET or None, kind=kind, initial=initial)
    filters = _filters_from_form(form, kind, today)
    report = _build_report(kind, filters, today)
    school = get_school_settings()
    period = _period_label(filters, kind, today)
    query = _export_query(request)
    return {
        "page_title": report["title"],
        "kind": kind,
        "form": form,
        "filters": filters,
        "today": today,
        "period": period,
        "school": school,
        "headers": report["headers"],
        "table": report["table"],
        "rows": report["rows"],
        "kpis": report["kpis"],
        "summary": report["summary"],
        "page": paginate(request, report["table"]),
        "extra_query": extra_query(request, drop=("page", "print")),
        "per_page": per_page_value(request),
        "excel_url": reverse("reports:excel", args=[kind]) + query,
        "pdf_url": reverse("reports:pdf", args=[kind]) + query,
        "print_url": reverse("reports:detail", args=[kind]) + (query + ("&" if query else "?")) + "print=1",
        "kinds": REPORT_KINDS,
        "is_snapshot": kind in SNAPSHOT_KINDS,
        "open_print": request.GET.get("print") == "1",
    }


@admin_required
@require_GET
def detail(request, kind):
    context = _report_context(request, kind)
    return render(request, "reports/detail.html", context)


@admin_required
@require_GET
def export_excel(request, kind):
    context = _report_context(request, kind)
    sheets = [
        {
            "title": "បញ្ជី",
            "heading": context["page_title"],
            "subtitle": f"{context['school'].school_name} · {context['period']}",
            "headers": context["headers"],
            "rows": context["table"],
        }
    ]
    if context["summary"] and context["kind"] == "revenue":
        sheets.append(
            {
                "title": "តាមវគ្គ",
                "heading": "ចំណូលតាមវគ្គ",
                "subtitle": context["period"],
                "headers": ["វគ្គ", "USD", "KHR"],
                "rows": [[row["label"], row["usd"], row["khr"]] for row in context["summary"]["by_course"]],
            }
        )
        sheets.append(
            {
                "title": "តាមថ្នាក់",
                "heading": "ចំណូលតាមថ្នាក់",
                "subtitle": context["period"],
                "headers": ["ថ្នាក់", "USD", "KHR"],
                "rows": [[row["label"], row["usd"], row["khr"]] for row in context["summary"]["by_class"]],
            }
        )
    filename = f"report-{kind}-{timezone.localdate().isoformat()}.xlsx"
    return excel_response(filename, sheets)


@admin_required
@require_GET
def export_pdf(request, kind):
    context = _report_context(request, kind)
    filename = f"report-{kind}-{timezone.localdate().isoformat()}.pdf"
    response = pdf_response(request, "reports/print.html", context, filename)
    if response:
        return response
    messages.info(request, "សូមជ្រើស Save as PDF ក្នុងប្រអប់ Print។")
    return redirect(context["print_url"])
