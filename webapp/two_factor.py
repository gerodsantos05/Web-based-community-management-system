from datetime import timedelta
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import UserProfile


TWO_FACTOR_CHALLENGE_SESSION_KEY = "two_factor_challenge"
TWO_FACTOR_VERIFIED_SESSION_KEY = "two_factor_verified_user_id"
TWO_FACTOR_CODE_LENGTH = 6
TWO_FACTOR_CODE_EXPIRY_MINUTES = 10


def _normalize_bool(value, default=False):
    if value is None:
        return default

    if isinstance(value, list):
        return bool(value)

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"0", "false", "off", "no", ""}:
            return False
        if lowered in {"1", "true", "on", "yes"}:
            return True

    return bool(value)


def _get_profile_state(user):
    if not user or not user.is_authenticated:
        return {}

    try:
        profile = user.userprofile
        return profile.settings_state if isinstance(profile.settings_state, dict) else {}
    except UserProfile.DoesNotExist:
        return {}


def is_two_factor_enabled(user):
    state = _get_profile_state(user)
    return _normalize_bool(state.get("security_2fa_enabled"), default=False)


def is_two_factor_confirmed(user):
    state = _get_profile_state(user)
    return _normalize_bool(state.get("security_2fa_confirmed"), default=False)


def requires_two_factor(user):
    return is_two_factor_enabled(user) and is_two_factor_confirmed(user)


def get_pending_two_factor_challenge(request):
    if not request:
        return None

    challenge = request.session.get(TWO_FACTOR_CHALLENGE_SESSION_KEY)
    return challenge if isinstance(challenge, dict) else None


def clear_two_factor_challenge(request):
    if not request:
        return

    request.session.pop(TWO_FACTOR_CHALLENGE_SESSION_KEY, None)
    request.session.modified = True


def clear_two_factor_verification(request):
    if not request:
        return

    request.session.pop(TWO_FACTOR_VERIFIED_SESSION_KEY, None)
    request.session.modified = True


def clear_two_factor_state(request):
    if not request:
        return

    clear_two_factor_challenge(request)
    clear_two_factor_verification(request)


def is_two_factor_session_verified(request, user):
    if not request or not user or not user.is_authenticated:
        return False

    verified_user_id = request.session.get(TWO_FACTOR_VERIFIED_SESSION_KEY)
    return verified_user_id == user.id


def mark_two_factor_session_verified(request, user):
    if not request or not user or not user.is_authenticated:
        return

    request.session[TWO_FACTOR_VERIFIED_SESSION_KEY] = user.id
    clear_two_factor_challenge(request)
    request.session.modified = True


def generate_two_factor_code():
    return f"{secrets.randbelow(10 ** TWO_FACTOR_CODE_LENGTH):0{TWO_FACTOR_CODE_LENGTH}d}"


def _build_two_factor_email(user, code, purpose):
    display_name = user.get_full_name() or user.username or "there"
    purpose_line = "sign in" if purpose == "login" else "finish turning on email code login"
    subject = "Your HappYness Project code"
    body = (
        f"Hi {display_name},\n\n"
        f"Your verification code is {code}.\n\n"
        f"Use this code to {purpose_line}. It expires in {TWO_FACTOR_CODE_EXPIRY_MINUTES} minutes.\n\n"
        f"If you did not request this code, you can ignore this email."
    )
    return subject, body


def _send_two_factor_email(user, code, purpose):
    recipient_email = str(getattr(user, "email", "") or "").strip()
    if not recipient_email:
        return False

    subject, body = _build_two_factor_email(user, code, purpose)
    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        message.send()
        return True
    except Exception as exc:
        print(f"[two_factor] Email send failed for {recipient_email}: {exc}")
        return False


def start_two_factor_challenge(request, user, purpose, return_url):
    if not request or not user or not user.is_authenticated:
        return False, "Unable to start verification. Please try again."

    recipient_email = str(getattr(user, "email", "") or "").strip()
    if not recipient_email:
        return False, "Please add an email address to your account first."

    code = generate_two_factor_code()
    challenge = {
        "user_id": user.id,
        "purpose": purpose,
        "return_url": return_url,
        "email": recipient_email,
        "code_hash": make_password(code),
        "attempts": 0,
        "expires_at": int((timezone.now() + timedelta(minutes=TWO_FACTOR_CODE_EXPIRY_MINUTES)).timestamp()),
    }

    request.session[TWO_FACTOR_CHALLENGE_SESSION_KEY] = challenge
    clear_two_factor_verification(request)

    if not _send_two_factor_email(user, code, purpose):
        clear_two_factor_challenge(request)
        return False, "We could not send a verification code right now. Please try again."

    request.session.modified = True
    return True, None


def touch_two_factor_challenge_attempt(request):
    challenge = get_pending_two_factor_challenge(request)
    if not challenge:
        return None

    challenge["attempts"] = int(challenge.get("attempts", 0) or 0) + 1
    request.session[TWO_FACTOR_CHALLENGE_SESSION_KEY] = challenge
    request.session.modified = True
    return challenge


def is_two_factor_challenge_expired(challenge):
    if not isinstance(challenge, dict):
        return True

    expires_at = challenge.get("expires_at")
    try:
        return float(expires_at) <= timezone.now().timestamp()
    except (TypeError, ValueError):
        return True


def is_two_factor_code_valid(challenge, submitted_code):
    if not isinstance(challenge, dict):
        return False

    code = str(submitted_code or "").strip()
    if not code:
        return False

    code_hash = str(challenge.get("code_hash") or "")
    if not code_hash:
        return False

    return check_password(code, code_hash)
