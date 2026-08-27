from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Course, CourseClass, Enrollment
from apps.academics.services import enroll_student, transfer_enrollment
from apps.students.models import Student


class StudentAndEnrollmentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin",
            password="secure-test-password",
        )
        self.course = Course.objects.create(
            name="English Level 1",
            fee_type=Course.FeeType.MONTHLY,
            default_fee=Decimal("30.00"),
            currency="USD",
        )
        self.class_morning = CourseClass.objects.create(
            course=self.course,
            name="English Level 1 – Morning",
            instructor_name="Sokha",
            start_date=date(2026, 8, 1),
            study_days=[0, 2, 4],
            start_time=time(8, 0),
            end_time=time(9, 30),
        )
        self.class_evening = CourseClass.objects.create(
            course=self.course,
            name="English Level 1 – Evening",
            instructor_name="Sokha",
            start_date=date(2026, 8, 1),
            study_days=[0, 2, 4],
            start_time=time(17, 0),
            end_time=time(18, 30),
        )

    def test_student_list_requires_login(self):
        response = self.client.get(reverse("students:list"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('students:list')}")

    def test_student_list_paginates_ten_or_twenty(self):
        self.client.force_login(self.user)
        for index in range(12):
            Student.objects.create(
                name_kh=f"សិស្ស {index}",
                name_en=f"Student {index}",
                gender=Student.Gender.MALE,
                phone=f"0120000{index:02d}",
            )
        ten = self.client.get(reverse("students:list"), {"per_page": 10})
        self.assertEqual(len(ten.context["students"].object_list), 10)
        self.assertContains(ten, "បង្ហាញ 1–10 ក្នុង 12")
        self.assertContains(ten, "១០ / ទំព័រ")
        page_two = self.client.get(reverse("students:list"), {"per_page": 10, "page": 2})
        self.assertEqual(len(page_two.context["students"].object_list), 2)
        self.assertContains(page_two, "បង្ហាញ 11–12 ក្នុង 12")
        invalid = self.client.get(reverse("students:list"), {"per_page": 99})
        self.assertEqual(invalid.context["per_page"], 20)
        self.assertEqual(len(invalid.context["students"].object_list), 12)

    def test_create_student_assigns_id(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("students:create"),
            {
                "name_kh": "សុខា",
                "name_en": "Sokha",
                "gender": Student.Gender.MALE,
                "phone": "012345678",
                "is_active": "on",
            },
        )
        student = Student.objects.get()
        year = timezone.localdate().year
        self.assertEqual(student.student_id, f"STU-{year}-0001")
        self.assertRedirects(response, reverse("students:list"))

    def test_student_can_enroll_in_multiple_classes(self):
        student = Student.objects.create(
            name_kh="សុខា",
            name_en="Sokha",
            gender=Student.Gender.MALE,
            phone="012345678",
        )
        first = enroll_student(student, self.class_morning, user=self.user)
        second = enroll_student(student, self.class_evening, user=self.user)
        self.assertEqual(first.status, Enrollment.Status.ACTIVE)
        self.assertEqual(second.status, Enrollment.Status.ACTIVE)
        self.assertEqual(student.enrollments.filter(status=Enrollment.Status.ACTIVE).count(), 2)

    def test_transfer_keeps_old_enrollment(self):
        student = Student.objects.create(
            name_kh="សុខា",
            name_en="Sokha",
            gender=Student.Gender.MALE,
            phone="012345678",
        )
        original = enroll_student(student, self.class_morning, user=self.user)
        transferred = transfer_enrollment(original, self.class_evening, user=self.user, note="ផ្លាស់ម៉ោង")
        original.refresh_from_db()
        self.assertEqual(original.status, Enrollment.Status.TRANSFERRED)
        self.assertEqual(transferred.status, Enrollment.Status.ACTIVE)
        self.assertEqual(transferred.transferred_from_id, original.pk)
        self.assertEqual(Enrollment.objects.filter(student=student).count(), 2)

    def test_enrollment_and_student_history_are_protected(self):
        student = Student.objects.create(
            name_kh="សុខា",
            name_en="Sokha",
            gender=Student.Gender.MALE,
            phone="012345678",
        )
        enrollment = enroll_student(student, self.class_morning)
        with self.assertRaises(ValidationError):
            enrollment.delete()
        with self.assertRaises(ProtectedError):
            student.delete()
        self.assertTrue(Enrollment.objects.filter(pk=enrollment.pk).exists())
