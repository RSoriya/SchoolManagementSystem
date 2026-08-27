from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("healthz/", views.healthz, name="healthz"),
    path("settings/", views.school_settings, name="settings"),
    path("settings/telegram/test/", views.telegram_test, name="telegram_test"),
    path("settings/telegram/alerts/", views.telegram_send_alerts, name="telegram_send_alerts"),
]
