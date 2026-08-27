from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    path("courses/", views.course_list, name="course_list"),
    path("courses/new/", views.course_create, name="course_create"),
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),
    path("courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course_delete"),
    path("classes/", views.class_list, name="class_list"),
    path("classes/new/", views.class_create, name="class_create"),
    path("classes/<int:pk>/", views.class_detail, name="class_detail"),
    path("classes/<int:pk>/edit/", views.class_edit, name="class_edit"),
    path("classes/<int:pk>/delete/", views.class_delete, name="class_delete"),
    path("classes/<int:pk>/enroll/", views.class_enroll, name="class_enroll"),
]
