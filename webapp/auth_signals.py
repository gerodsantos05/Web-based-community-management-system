from django.contrib.auth.models import User
from django.db import transaction
from allauth.account.signals import email_confirmed

from .models import UserProfile


def activate_verified_regular_account(sender, request, email_address, **kwargs):
    if not email_address.user_id:
        return

    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=email_address.user_id)
        profile = UserProfile.objects.select_for_update().filter(user_id=user.pk).first()
        if (
            not profile
            or not profile.email_verification_pending
            or user.is_staff
            or user.is_superuser
        ):
            return

        profile.email_verification_pending = False
        profile.save(update_fields=["email_verification_pending", "updated_at"])
        user.is_active = True
        user.save(update_fields=["is_active"])


def register_account_activation_signals():
    email_confirmed.connect(
        activate_verified_regular_account,
        dispatch_uid="webapp.activate_verified_regular_account",
    )
