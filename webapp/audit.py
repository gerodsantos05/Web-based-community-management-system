from contextvars import ContextVar

from django.apps import apps
from django.conf import settings
from django.db.models.signals import post_save, pre_delete, pre_save


_admin_actor = ContextVar("admin_activity_log_actor", default=None)
_request_events = ContextVar("admin_activity_log_events", default=None)

AUDITED_MODEL_SECTIONS = {
    settings.AUTH_USER_MODEL.lower(): "Users",
    "webapp.userprofile": "Users",
    "webapp.roleapplication": None,
    "webapp.beneficiaryassistancerecord": "Beneficiaries",
    "webapp.beneficiaryassistancefeedback": "Beneficiaries",
    "webapp.beneficiaryactivityfeedback": "Beneficiaries",
    "webapp.beneficiaryactivityattendance": "Beneficiaries",
    "webapp.activity": "Activities",
    "webapp.activityfundallocation": "Activities",
    "webapp.activitybeneficiaryassignment": "Activities",
    "webapp.volunteeractivityassignment": "Activities",
    "webapp.volunteerattendancerecord": "Volunteers",
    "webapp.volunteercertificate": "Volunteers",
    "webapp.volunteerojtschedule": "Volunteers",
    "webapp.volunteeradminmessage": "Volunteers",
    "webapp.volunteeradminmessageattachment": "Volunteers",
    "webapp.donation": "Donations",
    "webapp.itempledge": "Donations",
    "webapp.productinquiry": "Payments",
    "webapp.inventoryitem": "Inventory",
    "webapp.stockmovement": "Inventory",
}

IGNORED_FIELDS = {
    "created_at",
    "updated_at",
    "last_login",
    "official_receipt_number",
    "official_receipt_file",
    "official_receipt_generated_at",
    "verified_at",
    "verified_by",
    "reviewed_at",
    "reviewed_by",
    "created_by",
    "created_by_name",
    "last_modified_by",
    "last_modified_by_name",
    "volunteer_count",
}


def set_admin_actor(actor):
    return _admin_actor.set(actor)


def reset_admin_actor(token):
    _admin_actor.reset(token)


def begin_admin_audit_request():
    return _request_events.set([])


def reset_admin_audit_request(token):
    _request_events.reset(token)


PRIMARY_MODEL_PRIORITY = {
    "webapp.roleapplication": 0,
    "webapp.donation": 0,
    "webapp.itempledge": 0,
    "webapp.productinquiry": 0,
    "webapp.activity": 0,
    "webapp.inventoryitem": 0,
    "webapp.beneficiaryassistancerecord": 0,
    "webapp.beneficiaryactivityattendance": 0,
    "webapp.volunteerattendancerecord": 0,
    "webapp.volunteeradminmessage": 0,
    "webapp.userprofile": 1,
    settings.AUTH_USER_MODEL.lower(): 2,
}


def flush_admin_audit_request(actor, status_code):
    events = _request_events.get()
    if not actor or status_code >= 400 or not events:
        return

    status_events = [event for event in events if event["action"] in {"status", "approval"}]
    candidates = status_events or events
    primary = min(
        enumerate(candidates),
        key=lambda indexed: (
            PRIMARY_MODEL_PRIORITY.get(indexed[1]["model_label"], 50),
            indexed[0],
        ),
    )[1]

    if primary["action"] == "edit":
        changed_fields = []
        for event in events:
            if event["action"] != "edit":
                continue
            match = re.search(r"Changed:\s*(.+?)(?:\.|$)", event["details"])
            if match:
                changed_fields.extend(
                    field.strip()
                    for field in match.group(1).split(",")
                    if field.strip()
                )
        unique_fields = list(dict.fromkeys(changed_fields))
        if unique_fields:
            primary = dict(primary)
            primary["details"] = (
                f"Edited {primary['record_label']}. Changed: {', '.join(unique_fields)}."
            )

    _persist_log(actor, primary)


def _current_admin():
    actor = _admin_actor.get()
    if actor and getattr(actor, "is_authenticated", False) and actor.is_superuser:
        return actor
    return None


def _section_for(instance):
    model_label = instance._meta.label_lower
    if model_label == "webapp.roleapplication":
        return "Volunteers" if instance.role == "volunteer" else "Beneficiaries"
    if model_label == "webapp.userprofile":
        return {
            "volunteer": "Volunteers",
            "beneficiary": "Beneficiaries",
        }.get(instance.account_role, "Users")
    return AUDITED_MODEL_SECTIONS.get(model_label)


def _record_label(instance):
    if instance._meta.label_lower == settings.AUTH_USER_MODEL.lower():
        return instance.get_full_name().strip() or instance.get_username()
    if instance._meta.label_lower == "webapp.userprofile" and instance.user_id:
        return instance.user.get_full_name().strip() or instance.user.get_username()
    full_name = getattr(instance, "full_name", "")
    if full_name:
        return str(full_name).strip()[:255]
    for field_name in ("title", "name", "username", "reference_number", "item_name", "donor_name"):
        value = getattr(instance, field_name, None)
        if value:
            return str(value).strip()[:255]
    return f"{instance._meta.verbose_name.title()} #{instance.pk}"


def _field_display(field, value):
    if field.name == "is_active":
        return "Active" if value else "Inactive"
    return dict(field.flatchoices).get(value, value)


def _build_log_event(instance, action, details):
    actor = _current_admin()
    section = _section_for(instance)
    if actor is None or section is None:
        return None

    return {
        "model_label": instance._meta.label_lower,
        "admin_name": actor.get_full_name().strip() or actor.get_username(),
        "action": action,
        "section": section,
        "record_type": instance._meta.verbose_name.title()[:120],
        "record_id": str(instance.pk)[:64],
        "record_label": _record_label(instance),
        "details": details,
    }


def _persist_log(actor, event):
    from .models import AdminActivityLog

    AdminActivityLog.objects.create(
        admin=actor,
        admin_name=event["admin_name"][:150],
        action=event["action"],
        section=event["section"],
        record_type=event["record_type"],
        record_id=event["record_id"],
        record_label=event["record_label"],
        details=event["details"],
    )


def _write_log(instance, action, details):
    event = _build_log_event(instance, action, details)
    if event is None:
        return

    events = _request_events.get()
    if events is not None:
        events.append(event)
        return

    actor = _current_admin()
    if actor:
        _persist_log(actor, event)


def _capture_previous(sender, instance, raw=False, **kwargs):
    if raw or not instance.pk:
        instance._admin_audit_previous = None
        return

    field_names = [field.attname for field in sender._meta.concrete_fields]
    instance._admin_audit_previous = (
        sender._base_manager.filter(pk=instance.pk).values(*field_names).first()
    )


def _record_saved(sender, instance, created, raw=False, **kwargs):
    if raw:
        return

    if created:
        _write_log(instance, "create", f"Added {_record_label(instance)}.")
        return

    previous = getattr(instance, "_admin_audit_previous", None)
    if previous is None:
        return

    changed_fields = []
    status_change = None
    for field in sender._meta.concrete_fields:
        if field.primary_key or field.name in IGNORED_FIELDS:
            continue
        old_value = previous.get(field.attname)
        new_value = getattr(instance, field.attname)
        if old_value == new_value:
            continue
        changed_fields.append(field.verbose_name.title())
        if field.name in {"status", "is_active"}:
            status_change = (field, old_value, new_value)

    if not changed_fields:
        return

    section = _section_for(instance)
    action = "edit"
    if status_change:
        field, old_value, new_value = status_change
        if (
            instance._meta.label_lower == "webapp.roleapplication"
            and old_value == "pending"
            and new_value in {"approved", "rejected"}
        ):
            action = "approval"
            details = f"{_field_display(field, new_value)} {_record_label(instance)}."
        else:
            action = "status"
            details = (
                f"Changed {_field_display(field, old_value)} to "
                f"{_field_display(field, new_value)} for {_record_label(instance)}."
            )
    else:
        details = f"Edited {_record_label(instance)}. Changed: {', '.join(changed_fields)}."

    _write_log(instance, action, details)


def _record_deleted(sender, instance, **kwargs):
    _write_log(instance, "delete", f"Deleted {_record_label(instance)}.")


def register_audit_signals():
    for model_label in AUDITED_MODEL_SECTIONS:
        model = apps.get_model(model_label)
        pre_save.connect(
            _capture_previous,
            sender=model,
            weak=False,
            dispatch_uid=f"admin-audit-before-{model_label}",
        )
        post_save.connect(
            _record_saved,
            sender=model,
            weak=False,
            dispatch_uid=f"admin-audit-after-{model_label}",
        )
        pre_delete.connect(
            _record_deleted,
            sender=model,
            weak=False,
            dispatch_uid=f"admin-audit-delete-{model_label}",
        )