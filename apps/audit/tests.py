from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.audit.services import log_event


class AuditLogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin",
            password="secure-test-password",
            full_name_kh="អ្នកគ្រប់គ្រង",
        )
        self.client.force_login(self.user)

    def test_cannot_update_or_delete(self):
        event = log_event(
            action=AuditEvent.Action.SETTINGS_UPDATED,
            summary="កែការកំណត់",
            user=self.user,
        )
        with self.assertRaises(ValidationError):
            event.summary = "កែ"
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()
        self.assertTrue(AuditEvent.objects.filter(pk=event.pk).exists())

    def test_list_page_has_serial(self):
        log_event(
            action=AuditEvent.Action.STUDENT_CREATED,
            summary="បង្កើតសិស្ស STU-2026-0001",
            user=self.user,
        )
        response = self.client.get(reverse("audit:list"))
        self.assertContains(response, "ល.រ")
        self.assertContains(response, "បង្កើតសិស្ស")
        self.assertContains(response, "អ្នកគ្រប់គ្រង")
