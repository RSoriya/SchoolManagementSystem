from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.permissions import admin_required
from apps.core.pagination import extra_query, paginate, per_page_value

from .forms import PaymentForm, RefundForm
from .models import Payment, Receipt
from .payloads import payment_payload
from .services import collect_payment, enrollment_payload, payable_enrollments, refund_payment, void_payment


def _extra_query(request):
    return extra_query(request, drop=("page", "view", "print"))


def _error_message(exc):
    if hasattr(exc, "messages") and exc.messages:
        return exc.messages[0]
    return str(exc)


def _view_receipt(request):
    view_id = request.GET.get("view", "").strip()
    if not view_id.isdigit():
        return None
    return (
        Receipt.objects.select_related(
            "payment__student",
            "payment__course_class__course",
            "payment__method",
            "issued_by",
        )
        .filter(pk=view_id)
        .first()
    )


@admin_required
@require_GET
def payment_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    payments = Payment.objects.select_related(
        "student",
        "course_class__course",
        "method",
        "receipt",
        "refund",
    )
    if query:
        payments = payments.filter(
            Q(receipt__receipt_number__icontains=query)
            | Q(student__student_id__icontains=query)
            | Q(student__name_kh__icontains=query)
            | Q(student__name_en__icontains=query)
            | Q(course_class__name__icontains=query)
        )
    if status in {Payment.Status.COMPLETED, Payment.Status.VOIDED, Payment.Status.REFUNDED}:
        payments = payments.filter(status=status)
    page = paginate(request, payments)
    view_receipt = _view_receipt(request)
    return render(
        request,
        "billing/payment_list.html",
        {
            "page_title": "ការបង់ប្រាក់",
            "payments": page,
            "query": query,
            "status": status,
            "extra_query": _extra_query(request),
            "per_page": per_page_value(request),
            "payloads": {str(item.pk): payment_payload(item) for item in page.object_list},
            "refund_form": RefundForm(),
            "view_receipt": view_receipt,
            "open_receipt_modal": bool(view_receipt),
        },
    )


@admin_required
@require_http_methods(["GET", "POST"])
def payment_create(request):
    initial = {"paid_on": timezone.localdate()}
    enrollment_id = request.GET.get("enrollment", "").strip()
    if enrollment_id.isdigit():
        initial["enrollment"] = int(enrollment_id)
    form = PaymentForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            payment = collect_payment(
                enrollment=data["enrollment"],
                paid_on=data["paid_on"],
                tuition_amount=data["tuition_amount"],
                registration_fee=data.get("registration_fee"),
                late_fee=data.get("late_fee"),
                discount_amount=data.get("discount_amount"),
                scholarship_amount=data.get("scholarship_amount"),
                method=data["method"],
                transaction_reference=data.get("transaction_reference") or "",
                period_start=data.get("period_start"),
                period_end=data.get("period_end"),
                period_label=data.get("period_label") or "",
                next_due_date=data.get("next_due_date"),
                note=data.get("note") or "",
                user=request.user,
            )
            messages.success(request, f"បានទទួលបង់ប្រាក់។ បង្កាន់ដៃ {payment.receipt.receipt_number}")
            return redirect(payment.receipt)
        except ValidationError as exc:
            form.add_error(None, _error_message(exc))
    enrollments = payable_enrollments()
    return render(
        request,
        "billing/payment_form.html",
        {
            "page_title": "ទទួលបង់ប្រាក់",
            "form": form,
            "enrollment_payloads": {
                str(item.pk): enrollment_payload(item) for item in enrollments
            },
        },
    )


def _void_and_redirect(request, payment, next_url):
    try:
        void_payment(payment, user=request.user, reason=request.POST.get("void_reason", ""))
        messages.success(request, "បានលុបចោលការបង់ប្រាក់។ កំណត់ត្រាដើមនៅតែរក្សាទុក។")
    except ValidationError as exc:
        messages.error(request, _error_message(exc))
    return redirect(next_url)


@admin_required
@require_POST
def payment_void(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    return _void_and_redirect(request, payment, reverse("billing:payment_list"))


@admin_required
@require_POST
def payment_refund(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    form = RefundForm(request.POST)
    if form.is_valid():
        try:
            refund_payment(
                payment,
                method=form.cleaned_data["method"],
                reason=form.cleaned_data["reason"],
                refunded_on=form.cleaned_data["refunded_on"],
                user=request.user,
            )
            messages.success(request, "បានសងប្រាក់ពេញ។ កំណត់ត្រាបង់ដើមនៅតែរក្សាទុក។")
        except ValidationError as exc:
            messages.error(request, _error_message(exc))
    else:
        messages.error(request, "សូមបំពេញវិធីសង មូលហេតុ និងថ្ងៃសង។")
    return redirect("billing:payment_list")


@admin_required
@require_GET
def receipt_list(request):
    params = request.GET.copy()
    encoded = params.urlencode()
    url = reverse("billing:payment_list")
    return redirect(f"{url}?{encoded}" if encoded else url)


def _receipt_context(receipt, auto_print=False):
    return {
        "page_title": receipt.receipt_number,
        "receipt": receipt,
        "payment": receipt.payment,
        "auto_print": auto_print,
    }


@admin_required
@require_GET
def receipt_detail(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    return redirect(receipt)


@admin_required
@require_GET
def receipt_print(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    return redirect(f"{receipt.get_absolute_url()}&print=1")


@admin_required
@require_GET
def receipt_pdf(request, pk):
    receipt = get_object_or_404(
        Receipt.objects.select_related(
            "payment__student",
            "payment__course_class__course",
            "payment__method",
            "issued_by",
        ),
        pk=pk,
    )
    html = render_to_string(
        "billing/receipt_print.html",
        _receipt_context(receipt, auto_print=False),
        request=request,
    )
    try:
        from weasyprint import HTML

        pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{receipt.receipt_number}.pdf"'
        return response
    except Exception:
        messages.info(request, "សូមជ្រើស Save as PDF ក្នុងប្រអប់ Print។")
        return redirect(f"{receipt.get_absolute_url()}&print=1")


@admin_required
@require_POST
def receipt_void(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    return _void_and_redirect(request, receipt.payment, reverse("billing:payment_list"))
