from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from apps.academics.models import Course
from apps.core.constants import CURRENCY_CHOICES, format_money


class Payment(models.Model):
    class Status(models.TextChoices):
        COMPLETED = "completed", "បានបង់"
        VOIDED = "voided", "បានលុបចោល"
        REFUNDED = "refunded", "បានសងប្រាក់"

    enrollment = models.ForeignKey(
        "academics.Enrollment",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="ការចុះឈ្មោះ",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="សិស្ស",
    )
    course_class = models.ForeignKey(
        "academics.CourseClass",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="ថ្នាក់រៀន",
    )
    paid_on = models.DateField("ថ្ងៃបង់")
    currency = models.CharField("រូបិយប័ណ្ណ", max_length=3, choices=CURRENCY_CHOICES)
    tuition_amount = models.DecimalField("ថ្លៃសិក្សា", max_digits=12, decimal_places=2)
    registration_fee = models.DecimalField("ថ្លៃចុះឈ្មោះ", max_digits=12, decimal_places=2, default=0)
    late_fee = models.DecimalField("ថ្លៃយឺត", max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField("បញ្ចុះតម្លៃ", max_digits=12, decimal_places=2, default=0)
    scholarship_amount = models.DecimalField("អាហារូបករ", max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField("សរុប", max_digits=12, decimal_places=2)
    fee_amount = models.DecimalField("ថ្លៃវគ្គនៃរយៈពេល", max_digits=12, decimal_places=2, null=True, blank=True)
    balance_after = models.DecimalField("នៅជំពាក់បន្ទាប់ពីបង់", max_digits=12, decimal_places=2, null=True, blank=True)
    method = models.ForeignKey(
        "core.PaymentMethod",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="វិធីបង់ប្រាក់",
    )
    transaction_reference = models.CharField("លេខយោងប្រតិបត្តិការ", max_length=80, blank=True)
    period_type = models.CharField("ប្រភេទថ្លៃ", max_length=20, choices=Course.FeeType.choices)
    period_label = models.CharField("រយៈពេល", max_length=80, blank=True)
    period_start = models.DateField("ចាប់ផ្ដើមរយៈពេល", null=True, blank=True)
    period_end = models.DateField("បញ្ចប់រយៈពេល", null=True, blank=True)
    previous_due_date = models.DateField("ថ្ងៃផុតកំណត់មុនបង់", null=True, blank=True)
    next_due_date = models.DateField("ថ្ងៃផុតកំណត់បន្ទាប់", null=True, blank=True)
    note = models.CharField("កំណត់ចំណាំ", max_length=255, blank=True)
    status = models.CharField("ស្ថានភាព", max_length=20, choices=Status.choices, default=Status.COMPLETED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_payments",
        verbose_name="ទទួលដោយ",
    )
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="voided_payments",
    )
    void_reason = models.CharField("មូលហេតុលុបចោល", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-paid_on", "-created_at"]
        verbose_name = "ការបង់ប្រាក់"
        verbose_name_plural = "ការបង់ប្រាក់"
        indexes = [
            models.Index(fields=["-paid_on", "-created_at"]),
            models.Index(fields=["status"]),
        ]
        permissions = [
            ("collect_payment", "Can collect payments"),
            ("void_payment", "Can void payments"),
            ("refund_payment", "Can refund payments"),
        ]

    def __str__(self):
        return f"{self.student} · {self.total_display} ({self.paid_on})"

    def delete(self, using=None, keep_parents=False):
        raise ValidationError("ប្រវត្តិបង់ប្រាក់មិនត្រូវលុបទេ។")

    def get_absolute_url(self):
        try:
            return self.receipt.get_absolute_url()
        except Receipt.DoesNotExist:
            return reverse("billing:payment_list")

    @property
    def is_voided(self):
        return self.status == self.Status.VOIDED

    @property
    def is_refunded(self):
        return self.status == self.Status.REFUNDED

    @property
    def is_partial(self):
        return self.balance_after is not None and self.balance_after > 0

    @property
    def remaining_display(self):
        if self.balance_after is None:
            return ""
        return format_money(self.balance_after, self.currency)

    @property
    def fee_display(self):
        if self.fee_amount is None:
            return ""
        return format_money(self.fee_amount, self.currency)

    @property
    def total_display(self):
        return format_money(self.total_amount, self.currency)

    def amount_display(self, amount):
        return format_money(amount, self.currency)

    def line_items(self):
        items = [
            {"label": "ថ្លៃសិក្សា", "amount": self.tuition_amount, "negative": False},
        ]
        extras = [
            ("ថ្លៃចុះឈ្មោះ", self.registration_fee, False),
            ("ថ្លៃយឺត", self.late_fee, False),
            ("បញ្ចុះតម្លៃ", self.discount_amount, True),
            ("អាហារូបករ", self.scholarship_amount, True),
        ]
        for label, amount, negative in extras:
            if amount and amount > 0:
                items.append({"label": label, "amount": amount, "negative": negative})
        for item in items:
            display = format_money(item["amount"], self.currency)
            item["display"] = f"- {display}" if item["negative"] else display
        return items


class Receipt(models.Model):
    class Status(models.TextChoices):
        ISSUED = "issued", "បានចេញ"
        VOIDED = "voided", "បានលុបចោល"

    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="receipt",
        verbose_name="ការបង់ប្រាក់",
    )
    receipt_number = models.CharField("លេខបង្កាន់ដៃ", max_length=24, unique=True, editable=False)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_receipts",
        verbose_name="ចេញដោយ",
    )
    issued_at = models.DateTimeField("ថ្ងៃចេញ", auto_now_add=True)
    status = models.CharField("ស្ថានភាព", max_length=20, choices=Status.choices, default=Status.ISSUED)
    school_name = models.CharField("ឈ្មោះសាលា", max_length=200)
    school_address = models.CharField("អាសយដ្ឋានសាលា", max_length=255, blank=True)
    school_phone = models.CharField("ទូរសព្ទសាលា", max_length=50, blank=True)
    student_id_snapshot = models.CharField("លេខសម្គាល់សិស្ស", max_length=20)
    student_name_kh = models.CharField("ឈ្មោះសិស្ស", max_length=150)
    student_name_en = models.CharField("ឈ្មោះអង់គ្លេស", max_length=150, blank=True)
    course_name = models.CharField("វគ្គសិក្សា", max_length=150)
    class_name = models.CharField("ថ្នាក់រៀន", max_length=150)
    issued_by_name = models.CharField("ឈ្មោះអ្នកចេញ", max_length=150, blank=True)

    class Meta:
        ordering = ["-issued_at"]
        verbose_name = "បង្កាន់ដៃ"
        verbose_name_plural = "បង្កាន់ដៃ"

    def __str__(self):
        return self.receipt_number

    def delete(self, using=None, keep_parents=False):
        raise ValidationError("បង្កាន់ដៃមិនត្រូវលុបទេ។")

    def get_absolute_url(self):
        return f"{reverse('billing:payment_list')}?view={self.pk}"

    @property
    def is_voided(self):
        return self.status == self.Status.VOIDED


class Refund(models.Model):
    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="refund",
        verbose_name="ការបង់ប្រាក់",
    )
    refunded_on = models.DateField("ថ្ងៃសង")
    amount = models.DecimalField("ចំនួនសង", max_digits=12, decimal_places=2)
    currency = models.CharField("រូបិយប័ណ្ណ", max_length=3, choices=CURRENCY_CHOICES)
    method = models.ForeignKey(
        "core.PaymentMethod",
        on_delete=models.PROTECT,
        related_name="refunds",
        verbose_name="វិធីសងប្រាក់",
    )
    reason = models.CharField("មូលហេតុ", max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_refunds",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-refunded_on", "-created_at"]
        verbose_name = "ការសងប្រាក់"
        verbose_name_plural = "ការសងប្រាក់"

    def __str__(self):
        return f"Refund · {self.payment} · {format_money(self.amount, self.currency)}"

    def delete(self, using=None, keep_parents=False):
        raise ValidationError("ប្រវត្តិសងប្រាក់មិនត្រូវលុបទេ។")
