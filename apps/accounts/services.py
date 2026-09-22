from django.db.models import Q

from .roles import ADMIN_GROUP_NAME, ROLE_GROUP_NAMES, assign_role, is_cashier, is_school_admin, is_teacher


def ensure_admin_group(user):
    """Backward-compatible alias: assign the Admin staff role."""
    return assign_role(user, ADMIN_GROUP_NAME)


def active_admin_count():
    from .models import User

    return (
        User.objects.filter(is_active=True)
        .filter(Q(is_superuser=True) | Q(groups__name=ADMIN_GROUP_NAME) | ~Q(groups__name__in=ROLE_GROUP_NAMES))
        .distinct()
        .count()
    )


def can_manage_account(actor, target):
    if not actor or not target:
        return False
    if is_school_admin(actor):
        return True
    if is_cashier(actor):
        return is_teacher(target)
    return False


def can_deactivate(target, actor):
    if not target.is_active:
        return False
    if actor and target.pk == actor.pk:
        return False
    if is_school_admin(target) and active_admin_count() <= 1:
        return False
    if actor and not is_school_admin(actor):
        return is_teacher(target)
    return True


def can_change_role(target, new_role, actor=None):
    if new_role == ADMIN_GROUP_NAME:
        return True
    if not is_school_admin(target):
        return True
    if actor and target.pk == getattr(actor, "pk", None) and active_admin_count() <= 1:
        return False
    if active_admin_count() <= 1:
        return False
    return True
