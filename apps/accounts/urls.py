from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import ThrottledLoginView

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        ThrottledLoginView.as_view(),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
]
