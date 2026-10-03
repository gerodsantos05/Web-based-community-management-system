from django.shortcuts import redirect
from django.urls import reverse

from .two_factor import is_two_factor_enabled, is_two_factor_session_verified


class TwoFactorChallengeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.challenge_path = reverse("two_factor_verify").rstrip("/")
        self.logout_path = reverse("logout").rstrip("/")
        self.settings_state_path = reverse("dashboard_settings_state_update").rstrip("/")

    def __call__(self, request):
        user = getattr(request, "user", None)
        path = (getattr(request, "path_info", "") or "").rstrip("/")

        if user and user.is_authenticated and not user.is_superuser:
            if not is_two_factor_enabled(user):
                request.session.pop("two_factor_verified_user_id", None)
            elif not is_two_factor_session_verified(request, user):
                if path not in {self.challenge_path, self.logout_path, self.settings_state_path}:
                    return redirect("two_factor_verify")

        return self.get_response(request)
