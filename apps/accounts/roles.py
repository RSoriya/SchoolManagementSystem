from django.contrib.auth.models import Group, Permission
from django.db.models import Q

ADMIN_GROUP_NAME = "Admin"
CASHIER_GROUP_NAME = "Cashier"
TEACHER_GROUP_NAME = "Teacher"

ROLE_GROUP_NAMES = (ADMIN_GROUP_NAME, CASHIER_GROUP_NAME, TEACHER_GROUP_NAME)

ROLE_CHOICES = (
    (ADMIN_GROUP_NAME, "អ្នកគ្រប់គ្រង"),
    (CASHIER_GROUP_NAME, "អ្នកគិតលុយ"),
    (TEACHER_GROUP_NAME, "គ្រូបង្រៀន"),
)

ROLE_LABELS = dict(ROLE_CHOICES)

SCHOOL_APP_LABELS = (
    "accounts",
    "students",
    "academics",
    "billing",
    "notifications",
    "reports",
    "audit",
    "core",
    "dashboard",
)

CASHIER_PERMISSIONS = (
    "students.view_student",
    "academics.view_course",
    "academics.view_courseclass",
    "academics.view_enrollment",
    "billing.view_payment",
    "billing.view_receipt",
    "billing.view_refund",
    "billing.collect_payment",
)

TEACHER_PERMISSIONS = (
    "students.view_student",
    "academics.view_course",
    "academics.view_courseclass",
    "academics.view_enrollment",
    "academics.view_attendancerecord",
    "academics.mark_attendance",
    "academics.view_assessment",
    "academics.add_assessment",
    "academics.view_scorerecord",
    "academics.mark_score",
)


def _permission(codename_or_full):
    if "." in codename_or_full:
        app_label, codename = codename_or_full.split(".", 1)
        return Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
    return Permission.objects.filter(codename=codename_or_full).first()


def sync_role_groups():
    """Create staff groups and attach Django permissions. Idempotent."""
    admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    cashier_group, _ = Group.objects.get_or_create(name=CASHIER_GROUP_NAME)
    teacher_group, _ = Group.objects.get_or_create(name=TEACHER_GROUP_NAME)

    school_perms = Permission.objects.filter(content_type__app_label__in=SCHOOL_APP_LABELS)
    if school_perms.exists():
        admin_group.permissions.set(school_perms)

    cashier_perms = [perm for perm in (_permission(code) for code in CASHIER_PERMISSIONS) if perm]
    if cashier_perms:
        cashier_group.permissions.set(cashier_perms)

    teacher_perms = [perm for perm in (_permission(code) for code in TEACHER_PERMISSIONS) if perm]
    if teacher_perms:
        teacher_group.permissions.set(teacher_perms)

    return {
        ADMIN_GROUP_NAME: admin_group,
        CASHIER_GROUP_NAME: cashier_group,
        TEACHER_GROUP_NAME: teacher_group,
    }


def assign_role(user, role_name):
    if role_name not in ROLE_GROUP_NAMES:
        raise ValueError(f"Unknown role: {role_name}")
    groups = sync_role_groups()
    user.groups.remove(*[groups[name] for name in ROLE_GROUP_NAMES])
    user.groups.add(groups[role_name])
    return user


def ensure_staff_role(user):
    """V1 accounts with no group become Admin so existing logins keep working."""
    if user.groups.filter(name__in=ROLE_GROUP_NAMES).exists():
        return user
    return assign_role(user, ADMIN_GROUP_NAME)


def user_role(user):
    if not getattr(user, "is_authenticated", False):
        return ""
    if user.is_superuser:
        return ADMIN_GROUP_NAME
    names = set(user.groups.filter(name__in=ROLE_GROUP_NAMES).values_list("name", flat=True))
    if ADMIN_GROUP_NAME in names:
        return ADMIN_GROUP_NAME
    if CASHIER_GROUP_NAME in names:
        return CASHIER_GROUP_NAME
    if TEACHER_GROUP_NAME in names:
        return TEACHER_GROUP_NAME
    return ADMIN_GROUP_NAME


def role_label(user):
    return ROLE_LABELS.get(user_role(user), ROLE_LABELS[ADMIN_GROUP_NAME])


def is_school_admin(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    names = set(user.groups.filter(name__in=ROLE_GROUP_NAMES).values_list("name", flat=True))
    if ADMIN_GROUP_NAME in names:
        return True
    return not names


def is_cashier(user):
    return user_role(user) == CASHIER_GROUP_NAME


def is_teacher(user):
    return user_role(user) == TEACHER_GROUP_NAME


def user_has_perm(user, perm):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or is_school_admin(user):
        return True
    return user.has_perm(perm)


def capability_map(user):
    if not getattr(user, "is_authenticated", False):
        return {}
    return {
        "view_student": user_has_perm(user, "students.view_student"),
        "add_student": user_has_perm(user, "students.add_student"),
        "change_student": user_has_perm(user, "students.change_student"),
        "delete_student": user_has_perm(user, "students.delete_student"),
        "enroll_student": user_has_perm(user, "students.enroll_student"),
        "change_enrollment": user_has_perm(user, "academics.change_enrollment_status"),
        "view_course": user_has_perm(user, "academics.view_course"),
        "add_course": user_has_perm(user, "academics.add_course"),
        "change_course": user_has_perm(user, "academics.change_course"),
        "delete_course": user_has_perm(user, "academics.delete_course"),
        "view_class": user_has_perm(user, "academics.view_courseclass"),
        "add_class": user_has_perm(user, "academics.add_courseclass"),
        "change_class": user_has_perm(user, "academics.change_courseclass"),
        "delete_class": user_has_perm(user, "academics.delete_courseclass"),
        "view_payment": user_has_perm(user, "billing.view_payment"),
        "collect_payment": user_has_perm(user, "billing.collect_payment"),
        "void_payment": user_has_perm(user, "billing.void_payment"),
        "refund_payment": user_has_perm(user, "billing.refund_payment"),
        "view_reports": user_has_perm(user, "billing.view_payment"),
        "view_attendance": user_has_perm(user, "academics.view_attendancerecord"),
        "mark_attendance": user_has_perm(user, "academics.mark_attendance"),
        "view_scores": user_has_perm(user, "academics.view_scorerecord"),
        "mark_scores": user_has_perm(user, "academics.mark_score"),
        "add_assessment": user_has_perm(user, "academics.add_assessment"),
        "manage_users": is_school_admin(user),
        "view_audit": is_school_admin(user),
        "manage_settings": is_school_admin(user),
    }


def instructor_queryset():
    from .models import User

    return (
        User.objects.filter(is_active=True)
        .filter(
            Q(is_superuser=True)
            | Q(groups__name__in=[ADMIN_GROUP_NAME, TEACHER_GROUP_NAME])
            | ~Q(groups__name__in=ROLE_GROUP_NAMES)
        )
        .distinct()
        .order_by("full_name_kh", "username")
    )
