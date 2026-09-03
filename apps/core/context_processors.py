from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError


def school_context(request):
    school = None
    school_name = settings.SCHOOL_NAME
    alert_count = 0
    can = {}
    role_label = ""
    try:
        from apps.core.models import SchoolSettings

        school = SchoolSettings.objects.first()
        if school and school.school_name:
            school_name = school.school_name
    except (OperationalError, ProgrammingError):
        school = None

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        try:
            from apps.accounts.roles import capability_map, role_label as staff_role_label, user_has_perm

            can = capability_map(user)
            role_label = staff_role_label(user)
            if user_has_perm(user, "billing.view_payment"):
                from apps.billing.services import due_soon_enrollments, overdue_enrollments

                alert_count = due_soon_enrollments().count() + overdue_enrollments().count()
        except (OperationalError, ProgrammingError):
            alert_count = 0

    return {
        "school_name": school_name,
        "school": school,
        "app_version": "0.14.2",
        "alert_count": alert_count,
        "can": can,
        "role_label": role_label,
    }
