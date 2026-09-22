from django.db import migrations, models


def set_khr(apps, schema_editor):
    Course = apps.get_model("academics", "Course")
    Course.objects.exclude(currency="KHR").update(currency="KHR")


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0006_attendance_late_status"),
    ]

    operations = [
        migrations.RunPython(set_khr, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="course",
            name="currency",
            field=models.CharField(
                choices=[("KHR", "KHR")],
                default="KHR",
                max_length=3,
                verbose_name="រូបិយប័ណ្ណ",
            ),
        ),
    ]
