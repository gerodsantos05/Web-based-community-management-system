import re
import smtplib
from types import SimpleNamespace
from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .adapters import RoleBasedSocialAccountAdapter
from .models import UserProfile


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="mandatory",
    ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION=True,
    DEFAULT_FROM_EMAIL="HappYness Project <gerodsantos05@gmail.com>",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AccountActivationTests(TestCase):
    def setUp(self):
        cache.clear()

    def signup(self, username="verify-user", email="verify@example.com"):
        return self.client.post(
            reverse("signup"),
            {
                "username": username,
                "email": email,
                "password1": "ValidPassword123!",
                "password2": "ValidPassword123!",
            },
        )

    def confirmation_url(self):
        match = re.search(r"/accounts/confirm-email/([^/\s]+)/", mail.outbox[0].body)
        self.assertIsNotNone(match, "Verification email should contain an allauth confirmation link")
        return reverse("account_confirm_email", args=[match.group(1)])

    def test_traditional_signup_requires_email_confirmation_then_activates(self):
        response = self.signup()

        user = User.objects.get(username="verify-user")
        profile = UserProfile.objects.get(user=user)
        address = EmailAddress.objects.get(user=user)
        self.assertRedirects(response, reverse("email_verification"))
        self.assertFalse(user.is_active)
        self.assertTrue(profile.email_verification_pending)
        self.assertFalse(address.verified)
        self.assertEqual(len(mail.outbox), 1)
        verification_email = mail.outbox[0]
        self.assertEqual(
            verification_email.from_email,
            "HappYness Project <gerodsantos05@gmail.com>",
        )
        self.assertTrue(
            verification_email.subject.endswith(
                "Verify your HappYness Project email address"
            )
        )
        self.assertEqual(len(verification_email.alternatives), 1)
        html_body, content_type = verification_email.alternatives[0]
        self.assertEqual(content_type, "text/html")
        self.assertIn("HAPPYNESS PROJECT", html_body)
        self.assertIn("Verify Email Address", html_body)
        self.assertIn("cid:happyness-project-logo", html_body)
        self.assertTrue(
            any(
                getattr(attachment, "get", lambda *_args: None)("Content-ID")
                == "<happyness-project-logo>"
                for attachment in verification_email.attachments
            )
        )
        self.assertContains(self.client.get(reverse("email_verification")), "Verify your email")

        confirmation_page = self.client.get(self.confirmation_url())
        self.assertContains(confirmation_page, "HappYness Project")
        self.assertContains(confirmation_page, "Confirm email address")
        self.assertContains(confirmation_page, "role=\"status\"")
        self.assertNotContains(confirmation_page, "<h2>Menu:</h2>")

        response = self.client.post(self.confirmation_url(), follow=True)
        user.refresh_from_db()
        profile.refresh_from_db()
        address.refresh_from_db()
        self.assertTrue(address.verified)
        self.assertTrue(user.is_active)
        self.assertFalse(profile.email_verification_pending)

    def test_signup_keeps_pending_account_when_verification_email_fails(self):
        with patch(
            "webapp.views.send_verification_email_to_address",
            side_effect=smtplib.SMTPException("SMTP unavailable"),
        ):
            response = self.client.post(
                reverse("signup"),
                {
                    "username": "verify-user",
                    "email": "verify@example.com",
                    "password1": "ValidPassword123!",
                    "password2": "ValidPassword123!",
                },
                follow=True,
            )

        user = User.objects.get(username="verify-user")
        self.assertEqual(response.redirect_chain, [(reverse("email_verification"), 302)])
        self.assertFalse(user.is_active)
        self.assertTrue(user.userprofile.email_verification_pending)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assertContains(response, "Your account was created")
        self.assertContains(response, "request another link")

    def test_signup_retry_for_pending_email_redirects_to_verification_recovery(self):
        self.signup()

        response = self.client.post(
            reverse("signup"),
            {
                "username": "verify-user-retry",
                "email": "verify@example.com",
                "password1": "ValidPassword123!",
                "password2": "ValidPassword123!",
            },
            follow=True,
        )

        self.assertEqual(response.redirect_chain, [(reverse("email_verification"), 302)])
        self.assertEqual(User.objects.filter(email__iexact="verify@example.com").count(), 1)
        self.assertContains(response, "already awaiting verification")

    def test_resend_reports_when_email_helper_does_not_send(self):
        self.signup()

        with patch(
            "webapp.views.send_verification_email_to_address",
            return_value=False,
        ):
            response = self.client.post(
                reverse("email_verification"),
                {"email": "verify@example.com"},
            )

        self.assertContains(response, "We could not send another verification email")
        self.assertContains(response, 'role="alert"')

    def test_invalid_email_confirmation_shows_branded_recovery_link(self):
        response = self.client.get(reverse("account_confirm_email", args=["invalid-key"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This email confirmation link is invalid or has expired.")
        self.assertContains(response, reverse("email_verification"))

    def test_admin_deactivation_is_not_overridden_by_old_confirmation_link(self):
        self.signup()
        user = User.objects.get(username="verify-user")
        admin = User.objects.create_superuser(
            username="activation-admin",
            email="activation-admin@example.com",
            password="AdminPassword123!",
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("update_regular_user_profile"),
            {
                "user_id": user.pk,
                "full_name": user.username,
                "username": user.username,
                "email": user.email,
                "phone": "",
                "gender": "",
                "address_line": "",
                "status": "inactive",
            },
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.userprofile.email_verification_pending)

        response = self.client.post(self.confirmation_url(), follow=True)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_verified_google_signup_is_active_immediately(self):
        user = User.objects.create_user(
            username="google-user",
            email="google@example.com",
            password=None,
            is_active=False,
        )
        sociallogin = SimpleNamespace(
            email_addresses=[SimpleNamespace(verified=True)],
        )
        request = RequestFactory().get("/")

        with patch(
            "allauth.socialaccount.adapter.DefaultSocialAccountAdapter.save_user",
            return_value=user,
        ):
            RoleBasedSocialAccountAdapter().save_user(request, sociallogin)

        user.refresh_from_db()
        profile = UserProfile.objects.get(user=user)
        self.assertTrue(user.is_active)
        self.assertFalse(profile.email_verification_pending)
        self.assertEqual(len(mail.outbox), 0)

    def test_google_verified_claim_activates_account_when_email_address_flag_is_missing(self):
        user = User.objects.create_user(
            username="google-claim-user",
            email="google-claim@example.com",
            password="ValidPassword123!",
            is_active=False,
        )
        sociallogin = SimpleNamespace(
            email_addresses=[SimpleNamespace(verified=False)],
            account=SimpleNamespace(
                provider="google",
                extra_data={"email_verified": True},
            ),
        )
        request = RequestFactory().get("/")

        with patch(
            "allauth.socialaccount.adapter.DefaultSocialAccountAdapter.save_user",
            return_value=user,
        ):
            RoleBasedSocialAccountAdapter().save_user(request, sociallogin)

        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_google_sociallogin_saves_new_user_as_active(self):
        user = User(
            username="google-sociallogin-user",
            email="google-sociallogin@example.com",
            first_name="Gerod",
            is_active=False,
        )
        sociallogin = SocialLogin(
            user=user,
            account=SocialAccount(
                provider="google",
                uid="google-sociallogin-uid",
                extra_data={"email_verified": True},
            ),
            email_addresses=[
                EmailAddress(
                    email="google-sociallogin@example.com",
                    primary=True,
                    verified=True,
                )
            ],
        )
        request = RequestFactory().get("/")
        request.session = {}

        RoleBasedSocialAccountAdapter().save_user(request, sociallogin)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(
            EmailAddress.objects.get(user=user).verified,
        )
        self.assertEqual(len(mail.outbox), 1)
        welcome_email = mail.outbox[0]
        self.assertEqual(welcome_email.subject, "Welcome to Happyness Project!")
        self.assertEqual(welcome_email.to, ["google-sociallogin@example.com"])
        self.assertIn("Hi Gerod,", welcome_email.body)
        self.assertEqual(len(welcome_email.alternatives), 1)
        html_body, content_type = welcome_email.alternatives[0]
        self.assertEqual(content_type, "text/html")
        self.assertIn("HAPPYNESS PROJECT", html_body)
        self.assertIn("Welcome to HappYness Project!", html_body)
        self.assertIn("COMMUNITY / CARE / OPPORTUNITY", html_body)
        self.assertIn("cid:happyness-project-logo", html_body)
        self.assertTrue(
            any(
                getattr(attachment, "get", lambda *_args: None)("Content-ID")
                == "<happyness-project-logo>"
                for attachment in welcome_email.attachments
            )
        )

    def test_google_login_recovers_pending_account_but_preserves_admin_deactivation(self):
        request = RequestFactory().get("/")
        adapter = RoleBasedSocialAccountAdapter()

        for username, pending, expected_active in (
            ("pending-google-user", True, True),
            ("admin-disabled-google-user", False, False),
        ):
            with self.subTest(username=username):
                user = User.objects.create_user(
                    username=username,
                    email=f"{username}@example.com",
                    password="ValidPassword123!",
                    is_active=False,
                )
                UserProfile.objects.create(
                    user=user,
                    email_verification_pending=pending,
                )
                account = SocialAccount.objects.create(
                    user=user,
                    provider="google",
                    uid=username,
                    extra_data={"email_verified": True},
                )
                sociallogin = SocialLogin(
                    user=user,
                    account=account,
                    email_addresses=[
                        EmailAddress(
                            email=user.email,
                            primary=True,
                            verified=True,
                        )
                    ],
                )

                adapter.pre_social_login(request, sociallogin)

                user.refresh_from_db()
                self.assertEqual(user.is_active, expected_active)
                self.assertFalse(user.userprofile.email_verification_pending)

    def test_unverified_google_signup_remains_inactive_pending_verification(self):
        user = User.objects.create_user(
            username="unverified-google-user",
            email="unverified-google@example.com",
            password="ValidPassword123!",
            is_active=False,
        )
        sociallogin = SimpleNamespace(
            email_addresses=[SimpleNamespace(verified=False)],
        )
        request = RequestFactory().get("/")
        request.session = {}

        with patch(
            "allauth.socialaccount.adapter.DefaultSocialAccountAdapter.save_user",
            return_value=user,
        ):
            RoleBasedSocialAccountAdapter().save_user(request, sociallogin)

        user.refresh_from_db()
        profile = UserProfile.objects.get(user=user)
        self.assertFalse(user.is_active)
        self.assertTrue(profile.email_verification_pending)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(
            request.session["pending_email_verification"],
            "unverified-google@example.com",
        )
