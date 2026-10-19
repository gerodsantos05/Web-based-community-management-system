from django.shortcuts import redirect
from django.urls import reverse
from django.utils.cache import add_never_cache_headers

from .audit import (
    begin_admin_audit_request,
    flush_admin_audit_request,
    reset_admin_actor,
    reset_admin_audit_request,
    set_admin_actor,
)
from .two_factor import is_two_factor_enabled, is_two_factor_session_verified


class NoCacheAuthenticatedPagesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logout_path = reverse("logout").rstrip("/")

    def __call__(self, request):
        was_authenticated = bool(
            getattr(getattr(request, "user", None), "is_authenticated", False)
        )
        is_logout_request = (getattr(request, "path_info", "") or "").rstrip("/") == self.logout_path

        response = self.get_response(request)
        if was_authenticated or is_logout_request:
            add_never_cache_headers(response)
        return response


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


class AdminAuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        actor = getattr(request, "user", None)
        actor = actor if actor and actor.is_authenticated and actor.is_superuser else None
        actor_token = set_admin_actor(actor)
        events_token = begin_admin_audit_request()
        try:
            response = self.get_response(request)
            flush_admin_audit_request(actor, response.status_code)
            return response
        finally:
            reset_admin_audit_request(events_token)
            reset_admin_actor(actor_token)