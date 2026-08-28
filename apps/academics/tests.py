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
        self.assertContains(class_page, 'data-add-open')
        self.assertContains(class_page, 'data-modal="form-modal"')
        self.assertContains(class_page, reverse("academics:class_enroll", args=[course_class.pk]))

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


class AttendanceTests(TestCase):
    def setUp(self):
        from apps.academics.services import enroll_student
        from apps.students.models import Student

        self.user = get_user_model().objects.create_user(
            username="admin",
            password="secure-test-password",
        )
        self.client.force_login(self.user)
        self.course = Course.objects.create(
            name="English Kids",
            fee_type=Course.FeeType.MONTHLY,
            default_fee=Decimal("30.00"),
            currency="USD",
        )
        self.course_class = CourseClass.objects.create(
            course=self.course,
            name="Kids A",
            start_date=date(2026, 8, 1),
            study_days=[0, 2, 4],
        )
        self.student = Student.objects.create(
            name_kh="សុខា",
            name_en="Sokha",
            gender="male",
            phone="012345678",
        )
        self.enrollment = enroll_student(self.student, self.course_class, user=self.user)

    def test_sheet_defaults_to_present_and_marks_attendance(self):
        from apps.academics.models import AttendanceRecord

        hub = self.client.get(self.course_class.get_absolute_url())
        self.assertContains(hub, "វត្តមាន")
        self.assertContains(hub, "ពិន្ទុ")
        self.assertContains(hub, "លទ្ធផល")
        self.assertContains(hub, self.course_class.get_attendance_url())
        self.assertContains(hub, self.course_class.get_scores_url())
        self.assertContains(hub, self.course_class.get_results_url())
        self.assertNotContains(hub, "រក្សាទុកវត្តមាន")

        sheet = self.client.get(
            self.course_class.get_attendance_url(),
            {"date": "2026-08-26"},
        )
        self.assertEqual(sheet.status_code, 200)
        self.assertContains(sheet, "សុខា")
        self.assertContains(sheet, self.student.student_id)
        self.assertContains(sheet, "ភេទ")
        self.assertContains(sheet, "យឺត")
        self.assertContains(sheet, "សុំច្បាប់")
        self.assertContains(sheet, "សរុប")
        self.assertContains(sheet, f'name="status_{self.enrollment.pk}"')
        self.assertContains(sheet, "រក្សាទុកវត្តមាន")
        response = self.client.post(
            self.course_class.get_attendance_url(),
            {
                "from": "2026-08-26",
                "to": "2026-08-26",
                f"status_{self.enrollment.pk}": AttendanceRecord.Status.ABSENT,
            },
        )
        self.assertRedirects(
            response,
            f"{self.course_class.get_attendance_url()}?from=2026-08-26&to=2026-08-26",
            fetch_redirect_response=False,
        )
        record = AttendanceRecord.objects.get()
        self.assertEqual(record.status, AttendanceRecord.Status.ABSENT)
        self.assertEqual(record.student, self.student)

    def test_edit_upserts_without_deleting(self):
        from apps.academics.attendance import mark_class_attendance
        from apps.academics.models import AttendanceRecord

        attended_on = date(2026, 8, 26)
        mark_class_attendance(
            self.course_class,
            attended_on,
            {self.enrollment.pk: AttendanceRecord.Status.PRESENT},
            user=self.user,
        )
        mark_class_attendance(
            self.course_class,
            attended_on,
            {self.enrollment.pk: AttendanceRecord.Status.EXCUSED},
            user=self.user,
        )
        self.assertEqual(AttendanceRecord.objects.count(), 1)
        self.assertEqual(AttendanceRecord.objects.get().status, AttendanceRecord.Status.EXCUSED)

    def test_cannot_hard_delete_attendance(self):
        from django.core.exceptions import ValidationError

        from apps.academics.attendance import mark_class_attendance
        from apps.academics.models import AttendanceRecord

        mark_class_attendance(
            self.course_class,
            date(2026, 8, 26),
            {self.enrollment.pk: AttendanceRecord.Status.PRESENT},
            user=self.user,
        )
        with self.assertRaises(ValidationError):
            AttendanceRecord.objects.get().delete()
        self.assertEqual(AttendanceRecord.objects.count(), 1)

    def test_roster_is_active_enrollments_only(self):
        from apps.academics.models import Enrollment

        self.enrollment.status = Enrollment.Status.COMPLETED
        self.enrollment.save(update_fields=["status"])
        hub = self.client.get(self.course_class.get_absolute_url())
        self.assertContains(hub, "បញ្ចប់")
        sheet = self.client.get(
            self.course_class.get_attendance_url(),
            {"date": "2026-08-26"},
        )
        self.assertContains(sheet, "មិនមានសិស្សកំពុងរៀន")
        self.assertNotContains(sheet, "រក្សាទុកវត្តមាន")

    def test_day_register_columns_and_allows_non_study_day(self):
        sheet = self.client.get(
            self.course_class.get_attendance_url(),
            {"date": "2026-08-25"},
        )
        self.assertContains(sheet, "ល.រ")
        self.assertContains(sheet, ">ID<")
        self.assertContains(sheet, "ឈ្មោះ")
        self.assertContains(sheet, "ភេទ")
        self.assertContains(sheet, "ថ្ងៃទី 25/08/2026")
        self.assertContains(sheet, "សរុប")
        self.assertContains(sheet, "សុំច្បាប់")
        self.assertContains(sheet, "អវត្តមាន")
        self.assertContains(sheet, f'name="status_{self.enrollment.pk}"')
        self.assertContains(sheet, "យឺត")
        self.assertContains(sheet, "ពីថ្ងៃ")
        self.assertContains(sheet, "២០ / ទំព័រ")
        self.assertContains(sheet, "បង្ហាញ")

    def test_summary_counts_selected_date_range(self):
        from apps.academics.attendance import mark_class_attendance
        from apps.academics.models import AttendanceRecord

        mark_class_attendance(
            self.course_class,
            date(2026, 7, 1),
            {self.enrollment.pk: AttendanceRecord.Status.PRESENT},
            user=self.user,
        )
        mark_class_attendance(
            self.course_class,
            date(2026, 8, 26),
            {self.enrollment.pk: AttendanceRecord.Status.ABSENT},
            user=self.user,
        )
        one_day = self.client.get(
            self.course_class.get_attendance_url(),
            {"from": "2026-08-26", "to": "2026-08-26"},
        )
        self.assertEqual(one_day.context["attendance_rows"][0]["summary"]["present"], 0)
        self.assertEqual(one_day.context["attendance_rows"][0]["summary"]["absent"], 1)
        self.assertContains(one_day, "រក្សាទុកវត្តមាន")
        spanned = self.client.get(
            self.course_class.get_attendance_url(),
            {"from": "2026-07-01", "to": "2026-08-26"},
        )
        summary = spanned.context["attendance_rows"][0]["summary"]
        self.assertEqual(summary["present"], 1)
        self.assertEqual(summary["absent"], 1)
        self.assertContains(spanned, "01/07/2026")
        self.assertContains(spanned, "26/08/2026")
        self.assertNotContains(spanned, "រក្សាទុកវត្តមាន")
        self.assertNotContains(spanned, f'name="status_{self.enrollment.pk}"')

    def test_list_and_class_detail_link(self):
        listing = self.client.get(reverse("academics:attendance_list"))
        self.assertRedirects(listing, reverse("academics:class_list"))
        old_sheet = self.client.get(
            reverse("academics:attendance_sheet", args=[self.course_class.pk]),
            {"date": "2026-08-26"},
        )
        self.assertRedirects(
            old_sheet,
            f"{self.course_class.get_attendance_url()}?from=2026-08-26&to=2026-08-26",
            fetch_redirect_response=False,
        )
        detail = self.client.get(self.course_class.get_absolute_url())
        self.assertContains(detail, "វត្តមាន")
        self.assertContains(detail, self.course_class.get_attendance_url())
        self.assertNotContains(detail, "រក្សាទុកវត្តមាន")
        nav = self.client.get(reverse("dashboard:index"))
        self.assertNotContains(nav, 'href="/attendance/"')

    def test_student_detail_shows_attendance_history(self):
        from apps.academics.attendance import mark_class_attendance
        from apps.academics.models import AttendanceRecord

        mark_class_attendance(
            self.course_class,
            date(2026, 8, 26),
            {self.enrollment.pk: AttendanceRecord.Status.ABSENT},
            user=self.user,
        )
        page = self.client.get(self.student.get_absolute_url())
        self.assertContains(page, "ប្រវត្តិវត្តមាន")
        self.assertContains(page, "អវត្តមាន")
        self.assertContains(page, "Kids A")
        listing = self.client.get(reverse("academics:class_list"))
        self.assertContains(listing, self.course_class.get_absolute_url())
        self.assertNotContains(listing, reverse("academics:attendance_sheet", args=[self.course_class.pk]))

    def test_cashier_does_not_see_student_attendance(self):
        from apps.accounts.roles import assign_role
        from apps.academics.attendance import mark_class_attendance
        from apps.academics.models import AttendanceRecord

        mark_class_attendance(
            self.course_class,
            date(2026, 8, 26),
            {self.enrollment.pk: AttendanceRecord.Status.ABSENT},
            user=self.user,
        )
        cashier = get_user_model().objects.create_user(
            username="cashier",
            password="secure-test-password",
        )
        assign_role(cashier, "Cashier")
        self.client.force_login(cashier)
        page = self.client.get(self.student.get_absolute_url())
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "ប្រវត្តិវត្តមាន")
        self.assertNotContains(page, "ប្រវត្តិពិន្ទុ")
        class_page = self.client.get(self.course_class.get_absolute_url())
        self.assertEqual(class_page.status_code, 200)
        self.assertNotContains(class_page, self.course_class.get_attendance_url())
        self.assertNotContains(class_page, self.course_class.get_scores_url())
        self.assertNotContains(class_page, self.course_class.get_results_url())
        self.assertEqual(self.client.get(self.course_class.get_attendance_url()).status_code, 403)
        self.assertEqual(self.client.get(self.course_class.get_scores_url()).status_code, 403)
        self.assertEqual(self.client.get(self.course_class.get_results_url()).status_code, 403)


class ScoreTests(TestCase):
    def setUp(self):
        from apps.academics.services import enroll_student
        from apps.students.models import Student

        self.user = get_user_model().objects.create_user(
            username="admin",
            password="secure-test-password",
        )
        self.client.force_login(self.user)
        self.course = Course.objects.create(
            name="English Kids",
            fee_type=Course.FeeType.MONTHLY,
            default_fee=Decimal("30.00"),
            currency="USD",
        )
        self.course_class = CourseClass.objects.create(
            course=self.course,
            name="Kids A",
            start_date=date(2026, 8, 1),
            study_days=[0, 2, 4],
        )
        self.student = Student.objects.create(
            name_kh="សុខា",
            name_en="Sokha",
            gender="male",
            phone="012345678",
        )
        self.enrollment = enroll_student(self.student, self.course_class, user=self.user)

    def test_create_exam_and_save_scores(self):
        from apps.academics.models import ScoreRecord

        listing = self.client.get(self.course_class.get_scores_url())
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, "បង្កើតប្រឡង")
        self.assertContains(listing, "data-add-open")
        self.assertContains(listing, 'data-modal="form-modal"')
        self.assertNotContains(listing, "xl:grid-cols-[1.1fr_0.9fr]")
        created = self.client.post(
            self.course_class.get_scores_url(),
            {"name": "ប្រឡងកណ្ដាលវគ្គ", "assessed_on": "2026-08-20", "max_score": "100"},
        )
        self.assertEqual(created.status_code, 302)
        sheet_url = created.url
        sheet = self.client.get(sheet_url)
        self.assertContains(sheet, "សុខា")
        self.assertContains(sheet, self.student.student_id)
        self.assertContains(sheet, "ភេទ")
        self.assertContains(sheet, "រក្សាទុកពិន្ទុ")
        self.assertContains(sheet, "សរុប")
        self.assertContains(sheet, "និទ្ទេស")
        saved = self.client.post(sheet_url, {f"score_{self.enrollment.pk}": "85"})
        self.assertEqual(saved.status_code, 302)
        record = ScoreRecord.objects.get()
        self.assertEqual(record.score, Decimal("85"))
        self.assertEqual(record.student, self.student)
        again = self.client.post(sheet_url, {f"score_{self.enrollment.pk}": "90"})
        self.assertEqual(again.status_code, 302)
        self.assertEqual(ScoreRecord.objects.count(), 1)
        self.assertEqual(ScoreRecord.objects.get().score, Decimal("90"))

    def test_cannot_hard_delete_score(self):
        from django.core.exceptions import ValidationError

        from apps.academics.models import Assessment, ScoreRecord
        from apps.academics.scores import save_class_scores

        assessment = Assessment.objects.create(
            course_class=self.course_class,
            name="Quiz 1",
            assessed_on=date(2026, 8, 20),
            max_score=Decimal("100"),
        )
        save_class_scores(assessment, {self.enrollment.pk: "70"}, user=self.user)
        with self.assertRaises(ValidationError):
            ScoreRecord.objects.get().delete()
        with self.assertRaises(ValidationError):
            assessment.delete()
        self.assertEqual(ScoreRecord.objects.count(), 1)

    def test_student_detail_shows_score_history(self):
        from apps.academics.models import Assessment
        from apps.academics.scores import save_class_scores

        assessment = Assessment.objects.create(
            course_class=self.course_class,
            name="ប្រឡងកណ្ដាលវគ្គ",
            assessed_on=date(2026, 8, 20),
            max_score=Decimal("100"),
        )
        save_class_scores(assessment, {self.enrollment.pk: "85"}, user=self.user)
        page = self.client.get(self.student.get_absolute_url())
        self.assertContains(page, "ប្រវត្តិពិន្ទុ")
        self.assertContains(page, "ប្រឡងកណ្ដាលវគ្គ")
        self.assertContains(page, "85")
        self.assertContains(page, "B")
        self.assertContains(page, "ល្អណាស់")

    def test_class_results_shows_total_average_and_grade(self):
        from apps.academics.models import Assessment
        from apps.academics.scores import letter_grade, save_class_scores

        self.assertEqual(letter_grade(Decimal("90"))["code"], "A")
        self.assertEqual(letter_grade(Decimal("49.99"))["code"], "F")
        midterm = Assessment.objects.create(
            course_class=self.course_class,
            name="ប្រឡងកណ្ដាលវគ្គ",
            assessed_on=date(2026, 8, 20),
            max_score=Decimal("100"),
        )
        quiz = Assessment.objects.create(
            course_class=self.course_class,
            name="Quiz 1",
            assessed_on=date(2026, 8, 10),
            max_score=Decimal("50"),
        )
        save_class_scores(midterm, {self.enrollment.pk: "80"}, user=self.user)
        save_class_scores(quiz, {self.enrollment.pk: "40"}, user=self.user)
        page = self.client.get(self.course_class.get_results_url())
        self.assertEqual(page.status_code, 200)
        row = page.context["result_rows"][0]
        self.assertEqual(row["total"], Decimal("120.00"))
        self.assertEqual(row["total_max"], Decimal("150.00"))
        self.assertEqual(row["percent"], Decimal("80.00"))
        self.assertEqual(row["grade"]["code"], "B")
        self.assertContains(page, "លទ្ធផល")
        self.assertContains(page, "English Kids")
        self.assertContains(page, "ប្រឡងកណ្ដាលវគ្គ")
        self.assertContains(page, "Quiz 1")
        self.assertContains(page, "និទ្ទេស")
        listing = self.client.get(reverse("academics:class_score_sheet", args=[self.course_class.pk, midterm.pk]))
        self.assertRedirects(
            listing,
            f"{self.course_class.get_scores_url()}?exam={midterm.pk}",
            fetch_redirect_response=False,
        )


