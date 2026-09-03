from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("healthz/", views.healthz, name="healthz"),
    path("settings/", views.school_settings, name="settings"),
    path("settings/methods/new/", views.payment_method_create, name="payment_method_create"),
    path("settings/methods/<int:pk>/edit/", views.payment_method_edit, name="payment_method_edit"),
    path("settings/methods/<int:pk>/delete/", views.payment_method_delete, name="payment_method_delete"),
    path("settings/telegram/chat-id/", views.telegram_detect_chat, name="telegram_detect_chat"),
    path("settings/telegram/test/", views.telegram_test, name="telegram_test"),
    path("settings/telegram/alerts/", views.telegram_send_alerts, name="telegram_send_alerts"),
]
