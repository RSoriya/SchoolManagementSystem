from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_alter_payment_options_alter_payment_status_refund"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="fee_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="ថ្លៃវគ្គនៃរយៈពេល",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="balance_after",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="នៅជំពាក់បន្ទាប់ពីបង់",
            ),
        ),
    ]
