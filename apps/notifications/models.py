from django.core.exceptions import ValidationError
from django.db import models


class NotificationLog(models.Model):
    class Kind(models.TextChoices):
        DUE_SOON = "due_soon", "ជិតដល់ថ្ងៃផុតកំណត់"
        OVERDUE = "overdue", "ហួសថ្ងៃផុតកំណត់"
        TEST = "test", "សារសាកល្បង"

    class Status(models.TextChoices):
        SENT = "sent", "បានផ្ញើ"
        FAILED = "failed", "បរាជ័យ"
        SKIPPED = "skipped", "រំលង"

    enrollment = models.ForeignKey(
        "academics.Enrollment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="notification_logs",
        verbose_name="ការចុះឈ្មោះ",
    )
    kind = models.CharField("ប្រភេទ", max_length=20, choices=Kind.choices)
    channel = models.CharField("ឆានែល", max_length=20, default="telegram")
    sent_on = models.DateField("ថ្ងៃផ្ញើ")
    status = models.CharField("ស្ថានភាព", max_length=20, choices=Status.choices)
    message = models.TextField("សារ", blank=True)
    error = models.CharField("កំហុស", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "ការជូនដំណឹង"
        verbose_name_plural = "ការជូនដំណឹង"
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "kind", "sent_on"],
                condition=models.Q(enrollment__isnull=False),
                name="unique_enrollment_notice_per_day",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.sent_on}"

    def delete(self, using=None, keep_parents=False):
        raise ValidationError("ប្រវត្តិការជូនដំណឹងមិនត្រូវលុបទេ។")
