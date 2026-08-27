from .models import AuditEvent


def _actor_name(user):
    if not user:
        return ""
    return (
        getattr(user, "full_name_kh", "")
        or user.get_full_name()
        or getattr(user, "username", "")
    )


def log_event(*, action, summary, user=None, obj=None, extra=None):
    object_type = ""
    object_id = ""
    object_label = ""
    if obj is not None:
        object_type = obj._meta.label_lower
        object_id = str(getattr(obj, "pk", "") or "")
        object_label = str(obj)[:255]
    return AuditEvent.objects.create(
        actor=user if getattr(user, "is_authenticated", False) else None,
        actor_name=_actor_name(user),
        action=action,
        object_type=object_type,
        object_id=object_id,
        object_label=object_label,
        summary=summary[:255],
        extra=extra or {},
    )
