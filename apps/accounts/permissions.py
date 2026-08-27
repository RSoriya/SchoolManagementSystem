from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

ADMIN_GROUP_NAME = "Admin"


def is_school_admin(user):
    """V1 treats every authenticated account as Admin.

    Later roles should check Django Groups or named permissions instead of a
    role switcher UI.
    """
    return user.is_authenticated


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not is_school_admin(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


def permission_required(perm):
    """Permission gate that stays Admin-wide in V1, but names the future perm."""

    def decorator(view_func):
        @admin_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.has_perm(perm) or is_school_admin(user):
                return view_func(request, *args, **kwargs)
            return redirect_to_login(request.get_full_path())

        return _wrapped

    return decorator
