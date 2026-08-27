from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditEvent(models.Model):
    class Action(models.TextChoices):
        PAYMENT_COLLECTED = "payment.collected", "ទទួលបង់ប្រាក់"
        PAYMENT_VOIDED = "payment.voided", "លុបចោលការបង់"
        PAYMENT_REFUNDED = "payment.refunded", "សងប្រាក់"
        STUDENT_CREATED = "student.created", "បង្កើតសិស្ស"
        STUDENT_UPDATED = "student.updated", "កែសិស្ស"
        STUDENT_DELETED = "student.deleted", "លុបសិស្ស"
        ENROLLMENT_CREATED = "enrollment.created", "ចុះឈ្មោះ"
        ENROLLMENT_TRANSFERRED = "enrollment.transferred", "ផ្ទេរថ្នាក់"
        ENROLLMENT_STATUS = "enrollment.status", "ប្ដូរស្ថានភាព"
        SETTINGS_UPDATED = "settings.updated", "កែការកំណត់"
        USER_CREATED = "user.created", "បង្កើតអ្នកប្រើ"
        USER_UPDATED = "user.updated", "កែអ្នកប្រើ"
        USER_DEACTIVATED = "user.deactivated", "ផ្អាកអ្នកប្រើ"
        LOGIN_FAILED = "login.failed", "ចូលប្រព័ន្ធបរាជ័យ"
        BACKUP_CREATED = "backup.created", "បម្រុងទុកទិន្នន័យ"
        TELEGRAM_SENT = "telegram.sent", "ផ្ញើ Telegram"
        TELEGRAM_FAILED = "telegram.failed", "Telegram បរាជ័យ"

    created_at = models.DateTimeField("ពេលវេលា", auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        verbose_name="អ្នកប្រើ",
    )
    actor_name = models.CharField("ឈ្មោះអ្នកប្រើ", max_length=150, blank=True)
    action = models.CharField("សកម្មភាព", max_length=40, choices=Action.choices)
    object_type = models.CharField("ប្រភេទ", max_length=40, blank=True)
    object_id = models.CharField("លេខសម្គាល់", max_length=40, blank=True)
    object_label = models.CharField("វត្ថុ", max_length=255, blank=True)
    summary = models.CharField("សេចក្ដីសង្ខេប", max_length=255)
    extra = models.JSONField("ព័ត៌មានបន្ថែម", default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Log"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.created_at} · {self.get_action_display()}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Audit Log មិនត្រូវកែបានទេ។")
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        raise ValidationError("Audit Log មិនត្រូវលុបទេ។")
