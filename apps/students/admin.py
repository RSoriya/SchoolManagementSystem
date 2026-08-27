from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "name_kh", "name_en", "phone", "is_active")
    search_fields = ("student_id", "name_kh", "name_en", "phone")
    readonly_fields = ("student_id",)
