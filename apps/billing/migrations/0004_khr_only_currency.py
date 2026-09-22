from django.db import migrations, models


def set_khr(apps, schema_editor):
    Payment = apps.get_model("billing", "Payment")
    Refund = apps.get_model("billing", "Refund")
    Payment.objects.exclude(currency="KHR").update(currency="KHR")
    Refund.objects.exclude(currency="KHR").update(currency="KHR")


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0003_payment_fee_amount_balance_after"),
    ]

    operations = [
        migrations.RunPython(set_khr, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="payment",
            name="currency",
            field=models.CharField(choices=[("KHR", "KHR")], max_length=3),
        ),
        migrations.AlterField(
            model_name="refund",
            name="currency",
            field=models.CharField(choices=[("KHR", "KHR")], max_length=3),
        ),
    ]
