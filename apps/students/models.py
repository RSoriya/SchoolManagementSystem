from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.services import allocate_student_id


class Student(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "ប្រុស"
        FEMALE = "female", "ស្រី"

    student_id = models.CharField("លេខសម្គាល់សិស្ស", max_length=20, unique=True, editable=False)
    photo = models.ImageField("រូបថត", upload_to="students/%Y/%m/", blank=True)
    name_kh = models.CharField("ឈ្មោះជាភាសាខ្មែរ", max_length=150)
    name_en = models.CharField("ឈ្មោះជាភាសាអង់គ្លេស", max_length=150)
    gender = models.CharField("ភេទ", max_length=10, choices=Gender.choices)
    date_of_birth = models.DateField("ថ្ងៃខែឆ្នាំកំណើត", null=True, blank=True)
    phone = models.CharField("លេខទូរសព្ទ", max_length=30)
    email = models.EmailField("អ៊ីមែល", blank=True)
    address = models.CharField("អាសយដ្ឋាន", max_length=255, blank=True)
    guardian_name = models.CharField("ឈ្មោះអាណាព្យាបាល", max_length=150, blank=True)
    guardian_phone = models.CharField("ទូរសព្ទអាណាព្យាបាល", max_length=30, blank=True)
    guardian_relationship = models.CharField("តំណាង", max_length=80, blank=True)
    notes = models.TextField("កំណត់ចំណាំ", blank=True)
    is_active = models.BooleanField("កំពុងប្រើ", default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_students",
        verbose_name="បង្កើតដោយ",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "សិស្ស"
        verbose_name_plural = "សិស្ស"
        permissions = [
            ("enroll_student", "Can enroll students in classes"),
        ]

    def __str__(self):
        return f"{self.student_id} · {self.name_kh}"

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = allocate_student_id()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("students:detail", kwargs={"student_id": self.student_id})

    @property
    def display_name(self):
        return self.name_kh or self.name_en

    @property
    def initials(self):
        source = self.name_en or self.name_kh
        return (source[:1] or "S").upper()
