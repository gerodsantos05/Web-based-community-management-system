import logging
import smtplib

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse

from .email_utils import attach_happyness_logo
from .models import UserProfile
from .two_factor import is_two_factor_confirmed, is_two_factor_enabled, start_two_factor_challenge


logger = logging.getLogger(__name__)


class RoleBasedAccountAdapter(DefaultAccountAdapter):
    def render_mail(self, template_prefix, email, context):
        message = super().render_mail(template_prefix, email, context)
        if not template_prefix.startswith("account/email/email_confirmation"):
            return message

        if message.content_subtype != "html" and not any(
            content_type == "text/html"
            for _content, content_type in message.alternatives
        ):
            html_body = render_to_string(
                f"{template_prefix}_message.html",
                context,
                request=context.get("request"),
            ).strip()
            message.attach_alternative(html_body, "text/html")

        attach_happyness_logo(message)
        return message

    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_authenticated and user.is_superuser:
            return reverse("admin_dashboard")

        if user.is_authenticated and is_two_factor_enabled(user):
            return_url = self._dashboard_url_for_user(user)
            purpose = "setup" if not is_two_factor_confirmed(user) else "login"
            started, error_message = start_two_factor_challenge(request, user, purpose, return_url)
            if started:
                return reverse("two_factor_verify")

            logout(request)
            return reverse("signin")

        return self._dashboard_url_for_user(user)

    def _dashboard_url_for_user(self, user):
        try:
            role = user.userprofile.account_role
        except UserProfile.DoesNotExist:
            role = UserProfile.ROLE_REGULAR

        if role == UserProfile.ROLE_BENEFICIARY:
            return reverse("user_dashboard")
        if role == UserProfile.ROLE_VOLUNTEER:
            return reverse("volunteer_dashboard")
        return reverse("home")


class RoleBasedSocialAccountAdapter(DefaultSocialAccountAdapter):
    def _has_verified_google_email(self, sociallogin):
        if any(address.verified for address in sociallogin.email_addresses):
            return True

        account = getattr(sociallogin, "account", None)
        if getattr(account, "provider", None) != "google":
            return False

        provider_data = getattr(account, "extra_data", {}) or {}
        return bool(
            provider_data.get("email_verified")
            or provider_data.get("verified_email")
        )

    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        account = getattr(sociallogin, "account", None)
        if (
            user
            and user.pk
            and getattr(account, "provider", None) == "google"
            and getattr(account, "user_id", None) == user.pk
            and self._has_verified_google_email(sociallogin)
        ):
            with transaction.atomic():
                locked_user = User.objects.select_for_update().get(pk=user.pk)
                profile = UserProfile.objects.select_for_update().filter(
                    user_id=locked_user.pk,
                    email_verification_pending=True,
                ).first()
                if (
                    profile
                    and not locked_user.is_staff
                    and not locked_user.is_superuser
                ):
                    profile.email_verification_pending = False
                    profile.save(
                        update_fields=["email_verification_pending", "updated_at"]
                    )
                    if not locked_user.is_active:
                        locked_user.is_active = True
                        locked_user.save(update_fields=["is_active"])

        return super().pre_social_login(request, sociallogin)

    def save_user(self, request, sociallogin, form=None):
        social_user = getattr(sociallogin, "user", None)
        user_was_not_saved = bool(
            social_user
            and (
                not social_user.pk
                or not User.objects.filter(pk=social_user.pk).exists()
            )
        )
        is_google_signup = (
            user_was_not_saved
            and getattr(getattr(sociallogin, "account", None), "provider", None)
            == "google"
        )
        email_verified = self._has_verified_google_email(sociallogin)
        user = super().save_user(request, sociallogin, form)
        profile, _created = UserProfile.objects.get_or_create(user=user)
        if profile.account_role is None:
            profile.account_role = UserProfile.ROLE_REGULAR
        profile.email_verification_pending = not email_verified
        profile.save(update_fields=["account_role", "email_verification_pending"])
        user.is_active = email_verified
        user.save(update_fields=["is_active"])
        if not email_verified and user.email:
            request.session["pending_email_verification"] = user.email
        elif is_google_signup and user.email:
            self._send_google_welcome_email(user, request)
        return user

    def _send_google_welcome_email(self, user, request):
        context = {
            "first_name": user.first_name or "there",
            "user": user,
        }
        message = EmailMultiAlternatives(
            subject="Welcome to Happyness Project!",
            body=render_to_string(
                "auth/google_welcome_email.txt",
                context,
                request=request,
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        message.attach_alternative(
            render_to_string(
                "auth/google_welcome_email.html",
                context,
                request=request,
            ),
            "text/html",
        )
        attach_happyness_logo(message)
        try:
            sent_count = message.send(fail_silently=False)
        except (OSError, smtplib.SMTPException):
            logger.exception(
                "Failed to send Google signup welcome email to user %s",
                user.pk,
            )
            return

        if sent_count != 1:
            logger.warning(
                "Google signup welcome email was not sent to user %s",
                user.pk,
            )
