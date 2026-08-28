from django.urls import reverse

from .roles import user_role


def user_payload(user):
    return {
        "username": user.username,
        "full_name_kh": user.full_name_kh,
        "phone_number": user.phone_number,
        "email": user.email,
        "is_active": user.is_active,
        "role": user_role(user),
        "label": user.full_name_kh or user.username,
        "edit_url": reverse("users:edit", args=[user.pk]),
        "delete_url": reverse("users:deactivate", args=[user.pk]),
    }
