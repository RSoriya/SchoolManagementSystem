from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("", views.student_list, name="list"),
    path("new/", views.student_create, name="create"),
    path("<str:student_id>/", views.student_detail, name="detail"),
    path("<str:student_id>/edit/", views.student_edit, name="edit"),
    path("<str:student_id>/delete/", views.student_delete, name="delete"),
    path(
        "<str:student_id>/enrollments/<int:enrollment_id>/transfer/",
        views.transfer,
        name="transfer",
    ),
    path(
        "<str:student_id>/enrollments/<int:enrollment_id>/<str:action>/",
        views.change_status,
        name="change_status",
    ),
]
