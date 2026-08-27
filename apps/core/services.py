from django.db import transaction
from django.utils import timezone

from .models import NumberSequence, SchoolSettings


def allocate_numbered_code(key, prefix, width, when=None):
    year = (when or timezone.localdate()).year
    with transaction.atomic():
        sequence, _created = NumberSequence.objects.select_for_update().get_or_create(
            key=key,
            year=year,
            defaults={"last_value": 0},
        )
        sequence.last_value += 1
        sequence.save(update_fields=["last_value"])
        return f"{prefix}-{year}-{sequence.last_value:0{width}d}"


def allocate_student_id(when=None):
    return allocate_numbered_code("STU", "STU", 4, when=when)


def allocate_receipt_number(when=None):
    return allocate_numbered_code("RCP", "RCP", 6, when=when)


def get_school_settings():
    return SchoolSettings.get_solo()
