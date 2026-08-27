from datetime import date, time, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Course, CourseClass
from apps.academics.services import enroll_student
from apps.billing.services import due_soon_enrollments, overdue_enrollments
from apps.core.models import SchoolSettings
from apps.core.services import get_school_settings
from apps.notifications.models import NotificationLog
from apps.notifications.services import send_due_alerts, send_test_message
from apps.students.models import Student


class FakeTelegramResponse:
    def read(self):
        return b'{"ok": true}'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class NotificationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin",
            password="secure-test-password",
        )
        self.client.force_login(self.user)
        self.school = get_school_settings()
        self.school.telegram_bot_token = "test-token"
        self.school.telegram_admin_chat_id = "12345"
        self.school.reminder_days_before_due = 3
        self.school.overdue_alert_daily = True
        self.school.save()
        self.course = Course.objects.create(
            name="English Level 1",
            fee_type=Course.FeeType.MONTHLY,
            default_fee=Decimal("30.00"),
            currency="USD",
        )
        self.course_class = CourseClass.objects.create(
            course=self.course,
            name="English Level 1 – Morning",
            start_date=date(2026, 8, 1),
            study_days=[0, 2, 4],
            start_time=time(8, 0),
            end_time=time(9, 30),
        )
        self.student = Student.objects.create(
            name_kh="សុខា",
            name_en="Sokha",
            gender=Student.Gender.MALE,
            phone="012345678",
        )

    def test_due_soon_and_overdue_selection(self):
        today = timezone.localdate()
        due_soon = enroll_student(
            self.student,
            self.course_class,
            user=self.user,
            next_due_date=today + timedelta(days=3),
        )
        other = Student.objects.create(
            name_kh="ដារ៉ា",
            name_en="Dara",
            gender=Student.Gender.MALE,
            phone="012345679",
        )
        overdue = enroll_student(
            other,
            self.course_class,
            user=self.user,
            next_due_date=today - timedelta(days=1),
        )
        self.assertIn(due_soon, due_soon_enrollments(today, days=3))
        self.assertNotIn(overdue, due_soon_enrollments(today, days=3))
        self.assertIn(overdue, overdue_enrollments(today))
        self.assertNotIn(due_soon, overdue_enrollments(today))

    @patch("apps.notifications.services.urllib.request.urlopen", return_value=FakeTelegramResponse())
    def test_send_due_alerts_once_per_day(self, _mock_urlopen):
        today = timezone.localdate()
        enrollment = enroll_student(
            self.student,
            self.course_class,
            user=self.user,
            next_due_date=today + timedelta(days=3),
        )
        first = send_due_alerts(user=self.user, today=today)
        second = send_due_alerts(user=self.user, today=today)
        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["sent"], 0)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(
            NotificationLog.objects.filter(
                enrollment=enrollment,
                kind=NotificationLog.Kind.DUE_SOON,
                sent_on=today,
            ).count(),
            1,
        )

    @patch("apps.notifications.services.urllib.request.urlopen", return_value=FakeTelegramResponse())
    def test_test_message_and_command(self, mock_urlopen):
        send_test_message(user=self.user)
        self.assertTrue(NotificationLog.objects.filter(kind=NotificationLog.Kind.TEST, status="sent").exists())
        out = StringIO()
        call_command("send_due_alerts", stdout=out)
        self.assertIn("sent=", out.getvalue())
        self.assertTrue(mock_urlopen.called)

    @override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="")
    def test_command_requires_telegram(self):
        self.school.telegram_bot_token = ""
        self.school.telegram_admin_chat_id = ""
        self.school.save()
        with self.assertRaises(CommandError):
            call_command("send_due_alerts")

    def test_settings_keeps_token_when_blank(self):
        response = self.client.post(
            reverse("core:settings"),
            {
                "school_name": "សាលាសាកល្បង",
                "address": "",
                "phone": "",
                "reminder_days_before_due": "3",
                "overdue_alert_daily": "on",
                "telegram_bot_token": "",
                "telegram_admin_chat_id": "12345",
            },
        )
        self.assertRedirects(response, reverse("core:settings"))
        school = SchoolSettings.objects.get(pk=1)
        self.assertEqual(school.telegram_bot_token, "test-token")
        self.assertEqual(school.school_name, "សាលាសាកល្បង")

    def test_notification_log_cannot_be_deleted(self):
        log = NotificationLog.objects.create(
            kind=NotificationLog.Kind.TEST,
            sent_on=timezone.localdate(),
            status=NotificationLog.Status.SENT,
            message="test",
        )
        with self.assertRaises(ValidationError):
            log.delete()
