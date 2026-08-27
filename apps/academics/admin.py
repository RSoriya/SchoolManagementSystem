from django.contrib import admin

from .models import Course, CourseClass, Enrollment


class CourseClassInline(admin.TabularInline):
    model = CourseClass
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "fee_type", "default_fee", "currency", "is_active")
    inlines = [CourseClassInline]


@admin.register(CourseClass)
class CourseClassAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "instructor_name", "start_date", "is_active")
    list_filter = ("course", "is_active")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course_class", "status", "enrolled_on", "next_due_date")
    list_filter = ("status",)
    search_fields = ("student__student_id", "student__name_kh", "course_class__name")

    def has_delete_permission(self, request, obj=None):
        return False
