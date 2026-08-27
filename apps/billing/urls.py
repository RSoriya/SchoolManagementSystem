from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("payments/", views.payment_list, name="payment_list"),
    path("payments/new/", views.payment_create, name="payment_create"),
    path("payments/<int:pk>/void/", views.payment_void, name="payment_void"),
    path("payments/<int:pk>/refund/", views.payment_refund, name="payment_refund"),
    path("receipts/", views.receipt_list, name="receipt_list"),
    path("receipts/<int:pk>/", views.receipt_detail, name="receipt_detail"),
    path("receipts/<int:pk>/print/", views.receipt_print, name="receipt_print"),
    path("receipts/<int:pk>/pdf/", views.receipt_pdf, name="receipt_pdf"),
    path("receipts/<int:pk>/void/", views.receipt_void, name="receipt_void"),
]
