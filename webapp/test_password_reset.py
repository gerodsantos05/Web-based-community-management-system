import re

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="HappYness Project <gerodsantos05@gmail.com>",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "password-reset-tests",
        }
    },
)
class PasswordResetFlowTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_reset_email_link_sets_a_new_password(self):
        user = User.objects.create_user(
            username="password-reset-user",
            email="password-reset@example.com",
            password="Old-password-123!",
        )

        response = self.client.post(
            reverse("password_reset_request"),
            {"email": user.email},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["message"],
            "If an account exists for that email, we've sent a reset link.",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].from_email,
            "HappYness Project <gerodsantos05@gmail.com>",
        )
        self.assertIn(user.email, mail.outbox[0].to)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        html_email = mail.outbox[0].alternatives[0][0]
        self.assertIn("HAPPYNESS PROJECT", html_email)
        self.assertIn('src="cid:happyness-project-logo"', html_email)
        self.assertIn("Reset Password", html_email)
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        self.assertEqual(mail.outbox[0].attachments[0].get("Content-ID"), "<happyness-project-logo>")
        self.assertRegex(html_email, r'href="https?://[^"]+/password-reset/')

        reset_link = re.search(r"(?P<path>/password-reset/\S+)", mail.outbox[0].body)
        self.assertIsNotNone(reset_link, mail.outbox[0].body)
        confirm_path = reset_link.group("path")
        confirm_response = self.client.get(confirm_path, follow=True)
        self.assertEqual(confirm_response.status_code, 200)
        self.assertContains(confirm_response, "Choose a new password")

        response = self.client.post(
            confirm_response.request["PATH_INFO"],
            {
                "new_password1": "CedarRiver!4827Moon",
                "new_password2": "CedarRiver!4827Moon",
            },
        )

        self.assertRedirects(response, reverse("password_reset_complete"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("CedarRiver!4827Moon"))

    def test_verified_google_only_account_can_set_a_local_password(self):
        user = User.objects.create_user(
            username="google-only-reset-user",
            email="google-reset@example.com",
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True,
        )

        response = self.client.post(
            reverse("password_reset_request"),
            {"email": user.email},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email, mail.outbox[0].to)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)

        reset_link = re.search(r"(?P<path>/password-reset/\S+)", mail.outbox[0].body)
        self.assertIsNotNone(reset_link, mail.outbox[0].body)
        confirm_response = self.client.get(reset_link.group("path"), follow=True)
        self.assertContains(confirm_response, "Choose a new password")

        response = self.client.post(
            confirm_response.request["PATH_INFO"],
            {
                "new_password1": "VerifiedGoogle!Password2026",
                "new_password2": "VerifiedGoogle!Password2026",
            },
        )

        self.assertRedirects(response, reverse("password_reset_complete"))
        user.refresh_from_db()
        self.assertTrue(user.has_usable_password())
        self.assertTrue(user.check_password("VerifiedGoogle!Password2026"))

    def test_unverified_google_only_account_does_not_receive_reset_email(self):
        user = User.objects.create_user(
            username="unverified-google-reset-user",
            email="unverified-google-reset@example.com",
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=False,
            primary=True,
        )

        response = self.client.post(
            reverse("password_reset_request"),
            {"email": user.email},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mail.outbox, [])

    def test_unknown_email_gets_same_confirmation_without_sending_mail(self):
        response = self.client.post(
            reverse("password_reset_request"),
            {"email": "unknown-password-reset@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["message"],
            "If an account exists for that email, we've sent a reset link.",
        )
        self.assertEqual(mail.outbox, [])

    def test_invalid_email_is_rejected(self):
        response = self.client.post(
            reverse("password_reset_request"),
            {"email": "not-an-email"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(mail.outbox, [])

    def test_sign_in_modal_posts_reset_requests_to_reset_endpoint(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'action="{reverse("password_reset_request")}"',
        )
