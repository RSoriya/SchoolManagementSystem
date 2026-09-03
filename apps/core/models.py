from django.conf import settings
from django.db import models


class SchoolSettings(models.Model):
    school_name = models.CharField("ឈ្មោះសាលា", max_length=200)
    address = models.CharField("អាសយដ្ឋាន", max_length=255, blank=True)
    phone = models.CharField("លេខទូរសព្ទ", max_length=50, blank=True)
    logo = models.ImageField("និមិត្តសញ្ញា", upload_to="school/", blank=True)
    reminder_days_before_due = models.PositiveSmallIntegerField(
        "ជូនដំណឹងមុនថ្ងៃផុតកំណត់ (ថ្ងៃ)",
        default=3,
    )
    overdue_alert_daily = models.BooleanField("ជូនដំណឹង overdue រាល់ថ្ងៃ", default=True)
    telegram_bot_token = models.CharField("Telegram Bot Token", max_length=120, blank=True)
    telegram_admin_chat_id = models.CharField("Telegram Admin Chat ID", max_length=80, blank=True)

    class Meta:
        verbose_name = "ការកំណត់សាលា"
        verbose_name_plural = "ការកំណត់សាលា"

    def __str__(self):
        return self.school_name

    def save(self, *args, **kwargs):
        self.pk = 1
        if not self.school_name:
            self.school_name = settings.SCHOOL_NAME
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _created = cls.objects.get_or_create(
            pk=1,
            defaults={"school_name": settings.SCHOOL_NAME},
        )
        return obj


class PaymentMethod(models.Model):
    name = models.CharField("ឈ្មោះ", max_length=80)
    code = models.SlugField("កូដ", unique=True, max_length=40)
    requires_reference = models.BooleanField("ត្រូវការ Transaction Reference", default=True)
    is_active = models.BooleanField("កំពុងប្រើ", default=True)
    sort_order = models.PositiveSmallIntegerField("លំដាប់", default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "វិធីបង់ប្រាក់"
        verbose_name_plural = "វិធីបង់ប្រាក់"

    def __str__(self):
        return self.name


class NumberSequence(models.Model):
    key = models.CharField(max_length=20)
    year = models.PositiveIntegerField()
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["key", "year"], name="unique_number_sequence_per_year"),
        ]

    def __str__(self):
        return f"{self.key}-{self.year}-{self.last_value}"
