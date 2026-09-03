from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.accounts.services import can_deactivate


class LoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="admin",
            password="secure-test-password",
            full_name_kh="អ្នកគ្រប់គ្រង",
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ចងចាំខ្ញុំ")
        self.assertContains(response, "remember_me")

    def test_remember_me_keeps_username_after_logout(self):
        self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "secure-test-password", "remember_me": "on"},
        )
        self.client.post(reverse("accounts:logout"))
        page = self.client.get(reverse("accounts:login"))
        self.assertContains(page, 'value="admin"')
        form = page.context["form"]
        self.assertEqual(form["username"].value(), "admin")
        self.assertTrue(form["remember_me"].value())

    def test_remember_me_keeps_session(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "secure-test-password", "remember_me": "on"},
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertFalse(self.client.session.get_expire_at_browser_close())
        self.assertGreaterEqual(self.client.session.get_expiry_age(), 60 * 60 * 24 * 29)

    def test_login_without_remember_me_clears_saved_username(self):
        self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "secure-test-password", "remember_me": "on"},
        )
        self.client.post(reverse("accounts:logout"))
        self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "secure-test-password"},
        )
        self.client.post(reverse("accounts:logout"))
        page = self.client.get(reverse("accounts:login"))
        self.assertNotEqual(page.context["form"]["username"].value(), "admin")

    def test_login_without_remember_me_expires_with_browser(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "secure-test-password"},
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_login_succeeds_with_csrf_check(self):
        client = Client(enforce_csrf_checks=True)
        login_page = client.get(reverse("accounts:login"))
        response = client.post(
            reverse("accounts:login"),
            {
                "username": "admin",
                "password": "secure-test-password",
                "csrfmiddlewaretoken": str(login_page.context["csrf_token"]),
            },
        )
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_stale_csrf_shows_khmer_retry_page(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "secure-test-password"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "សូមបើកទំព័រចូលឡើងវិញ", status_code=403)

    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "secure-test-password"},
        )
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_failed_login_is_audited(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AuditEvent.objects.filter(action=AuditEvent.Action.LOGIN_FAILED).exists())

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "secure-test-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(LOGIN_FAILURE_LIMIT=1, LOGIN_FAILURE_WINDOW=900)
    def test_login_is_throttled(self):
        cache.clear()
        self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "wrong-password"},
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "secure-test-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ច្រើនដងពេក")


class UserAdminTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.admin = self.User.objects.create_user(
            username="admin",
            password="secure-test-password",
            full_name_kh="អ្នកគ្រប់គ្រង",
        )
        self.client.force_login(self.admin)

    def test_user_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("users:list"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('users:list')}")

    def test_user_list_has_serial(self):
        response = self.client.get(reverse("users:list"))
        self.assertContains(response, "ល.រ")
        self.assertContains(response, "បន្ថែមអ្នកប្រើ")
        self.assertContains(response, "admin")

    def test_create_user_assigns_admin_group(self):
        response = self.client.post(
            reverse("users:create"),
            {
                "username": "cashier",
                "full_name_kh": "កេសៀរ",
                "phone_number": "012000000",
                "email": "",
                "password1": "Another-secure-pass1",
                "password2": "Another-secure-pass1",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("users:list"))
        user = self.User.objects.get(username="cashier")
        self.assertTrue(user.groups.filter(name="Admin").exists())
        self.assertTrue(AuditEvent.objects.filter(action=AuditEvent.Action.USER_CREATED).exists())

    def test_create_cashier_assigns_cashier_group(self):
        response = self.client.post(
            reverse("users:create"),
            {
                "username": "cashier",
                "full_name_kh": "កេសៀរ",
                "phone_number": "012000000",
                "email": "",
                "password1": "Another-secure-pass1",
                "password2": "Another-secure-pass1",
                "is_active": "on",
                "role": "Cashier",
            },
        )
        self.assertRedirects(response, reverse("users:list"))
        user = self.User.objects.get(username="cashier")
        self.assertTrue(user.groups.filter(name="Cashier").exists())
        self.assertFalse(user.groups.filter(name="Admin").exists())

    def test_cannot_deactivate_self_or_last_admin(self):
        self.assertFalse(can_deactivate(self.admin, self.admin))
        response = self.client.post(reverse("users:deactivate", args=[self.admin.pk]))
        self.assertRedirects(response, reverse("users:list"))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_deactivate_other_user(self):
        other = self.User.objects.create_user(username="other", password="secure-test-password")
        response = self.client.post(reverse("users:deactivate", args=[other.pk]))
        self.assertRedirects(response, reverse("users:list"))
        other.refresh_from_db()
        self.assertFalse(other.is_active)
        self.assertTrue(AuditEvent.objects.filter(action=AuditEvent.Action.USER_DEACTIVATED).exists())

    def test_cannot_deactivate_last_active_user_via_edit(self):
        response = self.client.post(
            reverse("users:edit", args=[self.admin.pk]),
            {
                "username": "admin",
                "full_name_kh": "អ្នកគ្រប់គ្រង",
                "phone_number": "",
                "email": "",
                "password1": "",
                "password2": "",
            },
        )
        self.assertRedirects(response, reverse("users:list"))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)


class StaffRoleTests(TestCase):
    def setUp(self):
        from datetime import date
        from decimal import Decimal

        from apps.academics.models import Course, CourseClass
        from apps.accounts.roles import assign_role

        self.User = get_user_model()
        self.admin = self.User.objects.create_user(
            username="admin",
            password="secure-test-password",
            full_name_kh="អ្នកគ្រប់គ្រង",
        )
        assign_role(self.admin, "Admin")
        self.cashier = self.User.objects.create_user(
            username="cashier",
            password="secure-test-password",
            full_name_kh="កេសៀរ",
        )
        assign_role(self.cashier, "Cashier")
        self.teacher = self.User.objects.create_user(
            username="teacher",
            password="secure-test-password",
            full_name_kh="គ្រូ",
        )
        assign_role(self.teacher, "Teacher")
        self.course = Course.objects.create(
            name="English Kids",
            fee_type="monthly",
            default_fee=Decimal("30.00"),
            currency="USD",
        )
        self.own_class = CourseClass.objects.create(
            course=self.course,
            name="Kids A",
            instructor=self.teacher,
            instructor_name="គ្រូ",
            start_date=date(2026, 8, 1),
            study_days=[0, 2, 4],
        )
        self.other_class = CourseClass.objects.create(
            course=self.course,
            name="Kids B",
            instructor_name="Other",
            start_date=date(2026, 8, 1),
            study_days=[1, 3],
        )

    def test_cashier_can_collect_but_not_manage_settings(self):
        self.client.force_login(self.cashier)
        self.assertEqual(self.client.get(reverse("billing:payment_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("billing:payment_create"), follow=True).status_code, 200)
        self.assertEqual(self.client.get(reverse("core:settings")).status_code, 403)
        self.assertEqual(self.client.get(reverse("users:list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("audit:list")).status_code, 403)
        nav = self.client.get(reverse("dashboard:index"))
        self.assertContains(nav, "ការបង់ប្រាក់")
        self.assertNotContains(nav, reverse("users:list"))
        self.assertContains(nav, "អ្នកគិតលុយ")

    def test_cashier_cannot_void_payment(self):
        self.client.force_login(self.cashier)
        response = self.client.post(reverse("billing:payment_void", args=[1]))
        self.assertEqual(response.status_code, 403)

    def test_cashier_can_add_and_edit_students_courses_classes(self):
        from apps.students.models import Student

        self.client.force_login(self.cashier)
        students = self.client.get(reverse("students:list"))
        self.assertContains(students, "+ បន្ថែមសិស្ស")
        courses = self.client.get(reverse("academics:course_list"))
        self.assertContains(courses, "+ បន្ថែមវគ្គ")
        classes = self.client.get(reverse("academics:class_list"))
        self.assertContains(classes, "+ បន្ថែមថ្នាក់")
        self.assertEqual(self.client.post(reverse("students:create"), {"from_modal": "1"}).status_code, 200)
        created = self.client.post(
            reverse("students:create"),
            {
                "name_kh": "រិទ្ធ",
                "name_en": "Rith",
                "gender": "male",
                "phone": "012000111",
                "is_active": "on",
            },
        )
        self.assertRedirects(created, reverse("students:list"))
        student = Student.objects.get(name_en="Rith")
        listing = self.client.get(reverse("students:list"))
        self.assertContains(listing, "កែ")
        self.assertNotContains(listing, 'data-delete-id=')
        self.assertEqual(self.client.get(reverse("academics:course_create"), follow=True).status_code, 200)
        self.assertEqual(self.client.get(reverse("academics:class_create"), follow=True).status_code, 200)
        edited = self.client.post(
            reverse("academics:course_edit", args=[self.course.pk]),
            {
                "name": "English Kids Plus",
                "fee_type": self.course.fee_type,
                "default_fee": "35.00",
                "currency": self.course.currency,
                "is_active": "on",
            },
        )
        self.assertRedirects(edited, reverse("academics:course_list"))
        self.course.refresh_from_db()
        self.assertEqual(self.course.name, "English Kids Plus")
        self.assertEqual(self.client.post(reverse("students:delete", args=[student.student_id])).status_code, 403)
        self.assertEqual(self.client.post(reverse("academics:course_delete", args=[self.course.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("academics:class_delete", args=[self.own_class.pk])).status_code, 403)
        hub = self.client.get(self.own_class.get_absolute_url())
        self.assertContains(hub, "+ ចុះឈ្មោះសិស្ស")

    def test_teacher_sees_only_own_classes(self):
        self.client.force_login(self.teacher)
        listing = self.client.get(reverse("academics:class_list"))
        self.assertContains(listing, "Kids A")
        self.assertNotContains(listing, "Kids B")
        self.assertContains(listing, self.own_class.get_absolute_url())
        self.assertEqual(self.client.get(self.own_class.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(self.other_class.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse("billing:payment_list")).status_code, 403)
        nav = self.client.get(reverse("dashboard:index"))
        self.assertNotContains(nav, reverse("billing:payment_list"))
        self.assertNotContains(nav, 'href="/attendance/"')
        self.assertContains(nav, reverse("academics:class_list"))
        self.assertContains(nav, "គ្រូបង្រៀន")

    def test_teacher_can_mark_own_class_not_other(self):
        from apps.academics.models import AttendanceRecord
        from apps.academics.services import enroll_student
        from apps.students.models import Student

        student = Student.objects.create(
            name_kh="វណ្ណា",
            name_en="Vanna",
            gender="female",
            phone="012111222",
        )
        enrollment = enroll_student(student, self.own_class, user=self.admin)
        self.client.force_login(self.teacher)
        listing = self.client.get(reverse("academics:attendance_list"))
        self.assertRedirects(listing, reverse("academics:class_list"))
        hub = self.client.get(self.own_class.get_absolute_url())
        self.assertContains(hub, self.own_class.get_attendance_url())
        self.assertContains(hub, self.own_class.get_scores_url())
        self.assertContains(hub, self.own_class.get_results_url())
        own_sheet = self.client.get(self.own_class.get_attendance_url())
        self.assertEqual(own_sheet.status_code, 200)
        self.assertContains(own_sheet, "រក្សាទុកវត្តមាន")
        self.assertEqual(self.client.get(self.own_class.get_results_url()).status_code, 200)
        self.assertEqual(self.client.get(self.own_class.get_results_excel_url()).status_code, 200)
        self.assertEqual(self.client.get(self.other_class.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(self.other_class.get_attendance_url()).status_code, 404)
        self.assertEqual(self.client.get(self.other_class.get_results_url()).status_code, 404)
        self.assertEqual(self.client.get(self.other_class.get_results_excel_url()).status_code, 404)
        self.assertEqual(self.client.get(self.other_class.get_results_pdf_url()).status_code, 404)
        response = self.client.post(
            self.own_class.get_attendance_url(),
            {
                "from": "2026-08-26",
                "to": "2026-08-26",
                f"status_{enrollment.pk}": AttendanceRecord.Status.PRESENT,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AttendanceRecord.objects.filter(enrollment=enrollment, status=AttendanceRecord.Status.PRESENT).exists()
        )

    def test_cashier_cannot_view_or_mark_attendance(self):
        self.client.force_login(self.cashier)
        self.assertRedirects(self.client.get(reverse("academics:attendance_list")), reverse("academics:class_list"))
        class_page = self.client.get(self.own_class.get_absolute_url())
        self.assertEqual(class_page.status_code, 200)
        self.assertNotContains(class_page, self.own_class.get_attendance_url())
        self.assertNotContains(class_page, self.own_class.get_scores_url())
        self.assertNotContains(class_page, self.own_class.get_results_url())
        self.assertEqual(self.client.get(self.own_class.get_attendance_url()).status_code, 403)
        self.assertEqual(self.client.get(self.own_class.get_scores_url()).status_code, 403)
        self.assertEqual(self.client.get(self.own_class.get_results_url()).status_code, 403)
        self.assertEqual(self.client.get(self.own_class.get_results_excel_url()).status_code, 403)
        self.assertEqual(self.client.get(self.own_class.get_results_pdf_url()).status_code, 403)
        self.assertEqual(self.client.get(reverse("reports:detail", args=["attendance"])).status_code, 403)
        nav = self.client.get(reverse("dashboard:index"))
        self.assertNotContains(nav, 'href="/attendance/"')

    def test_login_keeps_cashier_role(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "cashier", "password": "secure-test-password"},
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.cashier.refresh_from_db()
        self.assertTrue(self.cashier.groups.filter(name="Cashier").exists())
        self.assertFalse(self.cashier.groups.filter(name="Admin").exists())
