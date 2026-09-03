import os
import sqlite3
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.backup import create_backup, prune_backups, restore_backup, verify_backup
from apps.core.pagination import extra_query, paginate, per_page_value


class BackupTests(TestCase):
    def _file_db(self):
        folder = Path(tempfile.mkdtemp())
        source = folder / "app.sqlite3"
        connection = sqlite3.connect(source)
        connection.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY)")
        connection.commit()
        connection.close()
        return folder, source

    def test_backup_verify_and_restore_sqlite(self):
        folder, source = self._file_db()
        backup_dir = folder / "backups"
        with override_settings(
            BACKUP_DIR=backup_dir,
            BACKUP_KEEP_DAYS=30,
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(source)}},
        ):
            path = create_backup()
            self.assertTrue(path.exists())
            self.assertIn("integrity_check=ok", verify_backup(path))
            source.write_bytes(b"corrupted")
            restore_backup(path, yes=True)
            connection = sqlite3.connect(source)
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            connection.close()
            self.assertIn(("demo",), tables)

    def test_restore_requires_confirmation(self):
        folder, source = self._file_db()
        with override_settings(
            BACKUP_DIR=folder / "backups",
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(source)}},
        ):
            path = create_backup()
            with self.assertRaises(ValidationError):
                restore_backup(path, yes=False)

    def test_prune_keeps_30_days(self):
        folder, source = self._file_db()
        backup_dir = folder / "backups"
        backup_dir.mkdir()
        old = backup_dir / "school_old.sqlite3"
        old.write_bytes(source.read_bytes())
        old_mtime = timezone.now().timestamp() - (40 * 24 * 60 * 60)
        os.utime(old, (old_mtime, old_mtime))
        with override_settings(BACKUP_DIR=backup_dir, BACKUP_KEEP_DAYS=30):
            removed = prune_backups()
        self.assertEqual([path.name for path in removed], ["school_old.sqlite3"])
        self.assertFalse(old.exists())

    def test_management_command_writes_backup(self):
        folder, source = self._file_db()
        with override_settings(
            BACKUP_DIR=folder / "backups",
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(source)}},
        ):
            call_command("backup_database", "--verify")
        self.assertTrue(any((folder / "backups").glob("school_*.sqlite3")))

    def test_restore_command_requires_yes(self):
        folder, source = self._file_db()
        with override_settings(
            BACKUP_DIR=folder / "backups",
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(source)}},
        ):
            path = create_backup()
            with self.assertRaises(CommandError):
                call_command("restore_database", str(path))

    def test_settings_shows_backup_section(self):
        user = get_user_model().objects.create_user(username="admin", password="secure-test-password")
        self.client.force_login(user)
        response = self.client.get(reverse("core:settings"))
        self.assertContains(response, "បម្រុងទុកទិន្នន័យ")
        self.assertContains(response, "backup_database")
        self.assertContains(response, "ល.រ")
        self.assertContains(response, "ព័ត៌មានសាលា")
        self.assertContains(response, "វិធីបង់ប្រាក់")
        self.assertContains(response, "Telegram")
        self.assertContains(response, "data-add-open")
        self.assertContains(response, "កែ")
        self.assertContains(response, "លុប")
        self.assertContains(response, "data-delete-id")
        self.assertNotContains(response, "xl:grid-cols-4")

    def test_can_add_and_edit_payment_method(self):
        user = get_user_model().objects.create_user(username="admin", password="secure-test-password")
        self.client.force_login(user)
        created = self.client.post(
            reverse("core:payment_method_create"),
            {
                "name": "TrueMoney",
                "code": "truemoney",
                "requires_reference": "on",
                "is_active": "on",
                "sort_order": "6",
                "from_modal": "1",
            },
        )
        self.assertRedirects(created, reverse("core:settings"))
        from apps.core.models import PaymentMethod

        method = PaymentMethod.objects.get(code="truemoney")
        self.assertTrue(method.requires_reference)
        listing = self.client.get(reverse("core:settings"))
        self.assertContains(listing, "TrueMoney")
        edited = self.client.post(
            reverse("core:payment_method_edit", args=[method.pk]),
            {
                "name": "TrueMoney KH",
                "code": "truemoney",
                "is_active": "on",
                "sort_order": "6",
                "from_modal": "1",
            },
        )
        self.assertRedirects(edited, reverse("core:settings"))
        method.refresh_from_db()
        self.assertEqual(method.name, "TrueMoney KH")
        self.assertFalse(method.requires_reference)

    def test_can_delete_unused_payment_method(self):
        user = get_user_model().objects.create_user(username="admin", password="secure-test-password")
        self.client.force_login(user)
        from apps.core.models import PaymentMethod

        method = PaymentMethod.objects.create(
            name="TrueMoney",
            code="truemoney",
            requires_reference=True,
            is_active=True,
            sort_order=9,
        )
        deleted = self.client.post(reverse("core:payment_method_delete", args=[method.pk]), follow=True)
        self.assertFalse(PaymentMethod.objects.filter(pk=method.pk).exists())
        self.assertContains(deleted, "បានលុបវិធីបង់ប្រាក់ TrueMoney។")

    def test_cannot_delete_payment_method_with_history(self):
        from datetime import date, time
        from decimal import Decimal

        user = get_user_model().objects.create_user(username="admin", password="secure-test-password")
        self.client.force_login(user)
        from apps.academics.models import Course, CourseClass
        from apps.academics.services import enroll_student
        from apps.billing.services import collect_payment
        from apps.core.models import PaymentMethod
        from apps.students.models import Student

        method = PaymentMethod.objects.create(
            name="TrueMoney",
            code="truemoney",
            requires_reference=False,
            is_active=True,
            sort_order=9,
        )
        course = Course.objects.create(
            name="English Level 1",
            fee_type=Course.FeeType.MONTHLY,
            default_fee=Decimal("30.00"),
            currency="USD",
        )
        course_class = CourseClass.objects.create(
            course=course,
            name="Morning",
            start_date=date(2026, 8, 1),
            study_days=[0, 2, 4],
            start_time=time(8, 0),
            end_time=time(9, 30),
        )
        student = Student.objects.create(
            name_kh="សុខា",
            name_en="Sokha",
            gender=Student.Gender.MALE,
            phone="012345678",
        )
        enrollment = enroll_student(student, course_class, user=user, next_due_date=date(2026, 8, 1))
        collect_payment(
            enrollment=enrollment,
            paid_on=date(2026, 8, 1),
            tuition_amount=Decimal("30.00"),
            method=method,
            period_label="សីហា 2026",
            next_due_date=date(2026, 9, 1),
            user=user,
        )
        blocked = self.client.post(reverse("core:payment_method_delete", args=[method.pk]), follow=True)
        self.assertTrue(PaymentMethod.objects.filter(pk=method.pk).exists())
        self.assertContains(blocked, "មិនអាចលុបវិធីបង់ដែលមានប្រវត្តិបង់ ឬសងប្រាក់។")

    def test_settings_save_shows_toast(self):
        user = get_user_model().objects.create_user(username="admin", password="secure-test-password")
        self.client.force_login(user)
        from apps.core.services import get_school_settings

        school = get_school_settings()
        response = self.client.post(
            reverse("core:settings"),
            {
                "school_name": school.school_name or "Test School",
                "address": school.address,
                "phone": school.phone,
                "reminder_days_before_due": school.reminder_days_before_due,
                "overdue_alert_daily": "on",
                "telegram_admin_chat_id": school.telegram_admin_chat_id,
            },
            follow=True,
        )
        self.assertContains(response, "បានរក្សាទុកការកំណត់សាលា។")
        self.assertContains(response, "data-toast")
        self.assertContains(response, "toast-stack")


class HealthzTests(TestCase):
    def test_healthz_is_public(self):
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")


class SeedDemoDataTests(TestCase):
    def test_seed_demo_data_is_idempotent(self):
        get_user_model().objects.create_user(username="admin", password="secure-test-password")
        call_command("seed_demo_data")
        from apps.academics.models import Enrollment
        from apps.billing.models import Payment
        from apps.students.models import Student
        from apps.academics.models import AttendanceRecord

        students = Student.objects.count()
        enrollments = Enrollment.objects.count()
        payments = Payment.objects.count()
        attendance = AttendanceRecord.objects.count()
        self.assertGreaterEqual(students, 24)
        self.assertGreater(enrollments, 20)
        self.assertGreater(payments, 10)
        self.assertGreater(attendance, 10)
        call_command("seed_demo_data")
        self.assertEqual(Student.objects.count(), students)
        self.assertEqual(Enrollment.objects.count(), enrollments)
        self.assertEqual(Payment.objects.count(), payments)
        self.assertEqual(AttendanceRecord.objects.count(), attendance)


class PaginationTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_per_page_accepts_ten_or_twenty(self):
        self.assertEqual(per_page_value(self.factory.get("/")), 20)
        self.assertEqual(per_page_value(self.factory.get("/", {"per_page": "10"})), 10)
        self.assertEqual(per_page_value(self.factory.get("/", {"per_page": "99"})), 20)
        self.assertEqual(per_page_value(self.factory.get("/", {"per_page": "abc"})), 20)

    def test_paginate_splits_rows(self):
        page = paginate(self.factory.get("/", {"per_page": "10"}), list(range(12)))
        self.assertEqual(list(page.object_list), list(range(10)))
        self.assertEqual(page.paginator.num_pages, 2)

    def test_extra_query_keeps_filters(self):
        request = self.factory.get("/", {"q": "sok", "class": "3", "page": "2", "per_page": "10"})
        self.assertEqual(extra_query(request), "&q=sok&class=3&per_page=10")
