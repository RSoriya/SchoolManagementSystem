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
