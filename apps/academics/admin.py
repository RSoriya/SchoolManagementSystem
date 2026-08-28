from django.contrib import admin

from .models import Assessment, AttendanceRecord, Course, CourseClass, Enrollment, ScoreRecord


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


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("attended_on", "student", "course_class", "status", "marked_by")
    list_filter = ("status", "attended_on")
    search_fields = ("student__student_id", "student__name_kh", "course_class__name")
    readonly_fields = (
        "enrollment",
        "course_class",
        "student",
        "attended_on",
        "marked_by",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("name", "course_class", "assessed_on", "max_score")
    list_filter = ("assessed_on",)
    search_fields = ("name", "course_class__name")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ScoreRecord)
class ScoreRecordAdmin(admin.ModelAdmin):
    list_display = ("assessment", "student", "score", "marked_by")
    search_fields = ("student__student_id", "student__name_kh", "assessment__name")
    readonly_fields = (
        "assessment",
        "enrollment",
        "course_class",
        "student",
        "marked_by",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
