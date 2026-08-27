from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("reports/", views.index, name="index"),
    path("reports/<slug:kind>/", views.detail, name="detail"),
    path("reports/<slug:kind>/excel/", views.export_excel, name="excel"),
    path("reports/<slug:kind>/pdf/", views.export_pdf, name="pdf"),
]
