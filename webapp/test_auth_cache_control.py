from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthenticatedPageCacheControlTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cache-control-user",
            password="test-password",
        )

    def test_authenticated_page_is_not_cached(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("user_dashboard"))

        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("no-cache", response["Cache-Control"])
        self.assertIn("must-revalidate", response["Cache-Control"])

    def test_logout_response_is_not_cached_and_session_is_invalidated(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("logout"))

        self.assertIn("no-store", response["Cache-Control"])
        protected_response = self.client.get(reverse("user_dashboard"))
        self.assertEqual(protected_response.status_code, 302)
        self.assertIn(reverse("signin"), protected_response["Location"])
