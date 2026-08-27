from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError


def school_context(request):
    school = None
    school_name = settings.SCHOOL_NAME
    alert_count = 0
    try:
        from apps.core.models import SchoolSettings

        school = SchoolSettings.objects.first()
        if school and school.school_name:
            school_name = school.school_name
    except (OperationalError, ProgrammingError):
        school = None

    if getattr(request, "user", None) and request.user.is_authenticated:
        try:
            from apps.billing.services import due_soon_enrollments, overdue_enrollments

            alert_count = due_soon_enrollments().count() + overdue_enrollments().count()
        except (OperationalError, ProgrammingError):
            alert_count = 0

    return {
        "school_name": school_name,
        "school": school,
        "app_version": "0.6.0",
        "alert_count": alert_count,
    }
