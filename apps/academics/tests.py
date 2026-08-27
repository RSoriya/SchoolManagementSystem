from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.academics.models import Course, CourseClass


class CourseClassViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin",
            password="secure-test-password",
        )
        self.client.force_login(self.user)
        self.course = Course.objects.create(
            name="Computer Basic",
            fee_type=Course.FeeType.FULL_COURSE,
            default_fee=Decimal("120.00"),
            currency="USD",
        )

    def test_create_class_with_schedule(self):
        response = self.client.post(
            reverse("academics:class_create"),
            {
                "course": self.course.pk,
                "name": "Computer Basic – Morning",
                "instructor_name": "Dara",
                "start_date": "2026-09-01",
                "end_date": "2026-12-01",
                "study_days": ["0", "2", "4"],
                "start_time": "08:00",
                "end_time": "09:30",
                "is_active": "on",
            },
        )
        course_class = CourseClass.objects.get()
        self.assertRedirects(response, reverse("academics:class_list"))
        self.assertEqual(course_class.study_days, [0, 2, 4])
        self.assertEqual(course_class.start_time, time(8, 0))
        self.assertEqual(course_class.start_date, date(2026, 9, 1))

    def test_class_list_has_serial_and_modal(self):
        CourseClass.objects.create(
            course=self.course,
            name="Computer Basic – Morning",
            start_date=date(2026, 9, 1),
            study_days=[0, 2, 4],
        )
        response = self.client.get(reverse("academics:class_list"))
        self.assertContains(response, "ល.រ")
        self.assertContains(response, 'data-modal="form-modal"')
        self.assertContains(response, 'data-add-open')
        self.assertContains(response, "កែ")
        self.assertContains(response, "លុប")

    def test_course_and_class_detail_have_serial(self):
        course_class = CourseClass.objects.create(
            course=self.course,
            name="Computer Basic – Morning",
            instructor_name="Dara",
            start_date=date(2026, 9, 1),
            study_days=[0, 2, 4],
        )
        course_page = self.client.get(self.course.get_absolute_url())
        self.assertContains(course_page, "ល.រ")
        class_page = self.client.get(course_class.get_absolute_url())
        self.assertContains(class_page, "ល.រ")

    def test_delete_empty_class(self):
        course_class = CourseClass.objects.create(
            course=self.course,
            name="Computer Basic – Morning",
            start_date=date(2026, 9, 1),
            study_days=[0, 2, 4],
        )
        response = self.client.post(reverse("academics:class_delete", args=[course_class.pk]))
        self.assertRedirects(response, reverse("academics:class_list"))
        self.assertFalse(CourseClass.objects.filter(pk=course_class.pk).exists())

    def test_cannot_delete_class_with_enrollment(self):
        from apps.students.models import Student

        course_class = CourseClass.objects.create(
            course=self.course,
            name="Computer Basic – Morning",
            start_date=date(2026, 9, 1),
            study_days=[0, 2, 4],
        )
        student = Student.objects.create(
            name_kh="សុខា",
            name_en="Sokha",
            gender="male",
            phone="012345678",
        )
        from apps.academics.services import enroll_student

        enroll_student(student, course_class)
        response = self.client.post(reverse("academics:class_delete", args=[course_class.pk]))
        self.assertRedirects(response, reverse("academics:class_list"))
        self.assertTrue(CourseClass.objects.filter(pk=course_class.pk).exists())

    def test_course_list_renders(self):
        response = self.client.get(reverse("academics:course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Computer Basic")
