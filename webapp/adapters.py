from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import logout
from django.urls import reverse

from .models import UserProfile
from .two_factor import is_two_factor_confirmed, is_two_factor_enabled, start_two_factor_challenge


class RoleBasedAccountAdapter(DefaultAccountAdapter):
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
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        profile, _created = UserProfile.objects.get_or_create(user=user)
        if profile.account_role is None:
            profile.account_role = UserProfile.ROLE_REGULAR
            profile.save(update_fields=["account_role"])
        return user
