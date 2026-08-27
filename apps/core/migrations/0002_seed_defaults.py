from django.db import migrations


def seed_defaults(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    PaymentMethod = apps.get_model("core", "PaymentMethod")
    SchoolSettings = apps.get_model("core", "SchoolSettings")

    Group.objects.get_or_create(name="Admin")
    SchoolSettings.objects.get_or_create(
        pk=1,
        defaults={"school_name": "School Management System", "reminder_days_before_due": 3},
    )
    methods = [
        ("Cash", "cash", False, 1),
        ("ABA", "aba", True, 2),
        ("ACLEDA", "acleda", True, 3),
        ("Wing", "wing", True, 4),
        ("KHQR", "khqr", True, 5),
    ]
    for name, code, requires_reference, sort_order in methods:
        PaymentMethod.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "requires_reference": requires_reference,
                "sort_order": sort_order,
                "is_active": True,
            },
        )


def unseed_defaults(apps, schema_editor):
    PaymentMethod = apps.get_model("core", "PaymentMethod")
    PaymentMethod.objects.filter(code__in=["cash", "aba", "acleda", "wing", "khqr"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(seed_defaults, unseed_defaults),
    ]
