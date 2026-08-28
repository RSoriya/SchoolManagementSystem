from django.urls import path

from . import attendance_views, views

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
    path("classes/<int:pk>/attendance/", views.class_attendance, name="class_attendance"),
    path("classes/<int:pk>/scores/", views.class_scores, name="class_scores"),
    path("classes/<int:pk>/scores/<int:assessment_pk>/", views.class_score_sheet, name="class_score_sheet"),
    path("classes/<int:pk>/results/", views.class_results, name="class_results"),
    path("classes/<int:pk>/edit/", views.class_edit, name="class_edit"),
    path("classes/<int:pk>/delete/", views.class_delete, name="class_delete"),
    path("classes/<int:pk>/enroll/", views.class_enroll, name="class_enroll"),
    path("attendance/", attendance_views.attendance_list, name="attendance_list"),
    path("attendance/<int:pk>/", attendance_views.attendance_sheet, name="attendance_sheet"),
]
