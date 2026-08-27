from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class DashboardTests(TestCase):
    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("dashboard:index"))
        expected = f"{reverse('accounts:login')}?next={reverse('dashboard:index')}"
        self.assertRedirects(response, expected)

    def test_authenticated_admin_can_view_dashboard(self):
        user = get_user_model().objects.create_user(
            username="admin",
            password="secure-test-password",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ផ្ទាំងគ្រប់គ្រង")
        self.assertContains(response, "ស្វាគមន៍")
        self.assertContains(response, "page-list")
        self.assertContains(response, 'id="due-alerts"')
        self.assertContains(response, "របាយការណ៍")
        self.assertContains(response, reverse("users:list"))
        self.assertContains(response, "ល.រ")

