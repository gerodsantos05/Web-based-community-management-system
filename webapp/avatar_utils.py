from django.core.exceptions import ObjectDoesNotExist
from django.templatetags.static import static


DEFAULT_AVATAR_STATIC_PATH = "media/HPimages/default-avatar.svg"


def default_avatar_url():
    return static(DEFAULT_AVATAR_STATIC_PATH)


def avatar_url_for_user(user):
    fallback_url = default_avatar_url()
    if user is None:
        return fallback_url

    try:
        profile = user.userprofile
    except (AttributeError, ObjectDoesNotExist):
        return fallback_url

    avatar = getattr(profile, "avatar", None)
    if not avatar:
        return fallback_url

    try:
        return avatar.url
    except (OSError, ValueError):
        return fallback_url
