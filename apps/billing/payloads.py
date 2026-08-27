from django.urls import reverse

from .models import Receipt


def payment_payload(payment):
    receipt_number = ""
    receipt_url = ""
    try:
        receipt_number = payment.receipt.receipt_number
        receipt_url = payment.receipt.get_absolute_url()
    except Receipt.DoesNotExist:
        pass
    return {
        "label": receipt_number or payment.student.display_name,
        "name": f"{payment.student.name_kh} · {payment.total_display}",
        "total_display": payment.total_display,
        "void_url": reverse("billing:payment_void", args=[payment.pk]),
        "refund_url": reverse("billing:payment_refund", args=[payment.pk]),
        "receipt_url": receipt_url,
    }


def receipt_payload(receipt):
    return {
        "label": receipt.receipt_number,
        "name": f"{receipt.receipt_number} · {receipt.student_name_kh}",
        "void_url": reverse("billing:receipt_void", args=[receipt.pk]),
        "print_url": f"{receipt.get_absolute_url()}&print=1",
        "pdf_url": reverse("billing:receipt_pdf", args=[receipt.pk]),
    }
