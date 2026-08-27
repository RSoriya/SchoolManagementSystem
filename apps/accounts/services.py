from django.contrib.auth.models import Group

from .permissions import ADMIN_GROUP_NAME


def ensure_admin_group(user):
    group, _created = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    user.groups.add(group)
    return user


def active_admin_count():
    from .models import User

    return User.objects.filter(is_active=True).count()


def can_deactivate(target, actor):
    if not target.is_active:
        return False
    if actor and target.pk == actor.pk:
        return False
    if active_admin_count() <= 1:
        return False
    return True
