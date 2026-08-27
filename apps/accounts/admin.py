from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SchoolUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("ព័ត៌មានសាលា", {"fields": ("full_name_kh", "phone_number")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("ព័ត៌មានសាលា", {"fields": ("full_name_kh", "phone_number", "email")}),
    )
    list_display = ("username", "full_name_kh", "email", "is_staff", "is_active")

