from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from apps.core.constants import CURRENCY_CHOICES, format_weekdays


class Course(models.Model):
    class FeeType(models.TextChoices):
        MONTHLY = "monthly", "ប្រចាំខែ"
        FULL_COURSE = "full_course", "គិតតាមវគ្គ"
        ONE_TIME = "one_time", "មួយលើក"

    name = models.CharField("ឈ្មោះវគ្គ", max_length=150)
    name_kh = models.CharField("ឈ្មោះជាភាសាខ្មែរ", max_length=150, blank=True)
    description = models.TextField("ពិពណ៌នា", blank=True)
    fee_type = models.CharField("ប្រភេទថ្លៃ", max_length=20, choices=FeeType.choices)
    default_fee = models.DecimalField("ថ្លៃសិក្សា", max_digits=12, decimal_places=2)
    currency = models.CharField("រូបិយប័ណ្ណ", max_length=3, choices=CURRENCY_CHOICES, default="USD")
    is_active = models.BooleanField("កំពុងប្រើ", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "វគ្គសិក្សា"
        verbose_name_plural = "វគ្គសិក្សា"

    def __str__(self):
        return self.name_kh or self.name

    def get_absolute_url(self):
        return reverse("academics:course_detail", kwargs={"pk": self.pk})


class CourseClass(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="classes",
        verbose_name="វគ្គសិក្សា",
    )
    name = models.CharField("ឈ្មោះថ្នាក់", max_length=150)
    instructor_name = models.CharField("គ្រូបង្រៀន", max_length=150, blank=True)
    start_date = models.DateField("ថ្ងៃចាប់ផ្ដើម")
    end_date = models.DateField("ថ្ងៃបញ្ចប់", null=True, blank=True)
    study_days = models.JSONField("ថ្ងៃសិក្សា", default=list)
    start_time = models.TimeField("ម៉ោងចាប់ផ្ដើម", null=True, blank=True)
    end_time = models.TimeField("ម៉ោងបញ្ចប់", null=True, blank=True)
    is_active = models.BooleanField("កំពុងប្រើ", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "ថ្នាក់រៀន"
        verbose_name_plural = "ថ្នាក់រៀន"
        constraints = [
            models.UniqueConstraint(fields=["course", "name"], name="unique_class_name_per_course"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "ថ្ងៃបញ្ចប់ត្រូវនៅក្រោយថ្ងៃចាប់ផ្ដើម។"})
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "ម៉ោងបញ្ចប់ត្រូវនៅក្រោយម៉ោងចាប់ផ្ដើម។"})

    def get_absolute_url(self):
        return reverse("academics:class_detail", kwargs={"pk": self.pk})

    @property
    def study_days_display(self):
        return format_weekdays(self.study_days)

    @property
    def study_time_display(self):
        if self.start_time and self.end_time:
            return f"{self.start_time.strftime('%H:%M')} – {self.end_time.strftime('%H:%M')}"
        if self.start_time:
            return self.start_time.strftime("%H:%M")
        return "—"


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "កំពុងរៀន"
        SUSPENDED = "suspended", "ផ្អាក"
        DROPPED = "dropped", "បោះបង់"
        TRANSFERRED = "transferred", "ផ្ទេរ"
        COMPLETED = "completed", "បញ្ចប់"

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="សិស្ស",
    )
    course_class = models.ForeignKey(
        CourseClass,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="ថ្នាក់រៀន",
    )
    status = models.CharField("ស្ថានភាព", max_length=20, choices=Status.choices, default=Status.ACTIVE)
    enrolled_on = models.DateField("ថ្ងៃចុះឈ្មោះ")
    ended_on = models.DateField("ថ្ងៃបញ្ចប់", null=True, blank=True)
    next_due_date = models.DateField("Due Date បន្ទាប់", null=True, blank=True)
    note = models.CharField("កំណត់ចំណាំ", max_length=255, blank=True)
    transferred_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="transfer_targets",
        verbose_name="ផ្ទេរពី",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_enrollments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-enrolled_on", "-created_at"]
        verbose_name = "ការចុះឈ្មោះ"
        verbose_name_plural = "ការចុះឈ្មោះ"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course_class"],
                condition=models.Q(status="active"),
                name="unique_active_enrollment_per_class",
            ),
        ]
        permissions = [
            ("change_enrollment_status", "Can change enrollment status"),
        ]

    def __str__(self):
        return f"{self.student} → {self.course_class} ({self.get_status_display()})"

    def delete(self, using=None, keep_parents=False):
        raise ValidationError("ប្រវត្តិចុះឈ្មោះមិនត្រូវលុបទេ។")

    @property
    def is_open(self):
        return self.status in {self.Status.ACTIVE, self.Status.SUSPENDED}
