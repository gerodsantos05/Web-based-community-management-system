from datetime import timedelta
import re

from django.db import migrations


SYSTEM_FIELD_NAMES = {
    "createdat",
    "updatedat",
    "lastlogin",
    "officialreceiptnumber",
    "officialreceiptfile",
    "officialreceiptgeneratedat",
    "verifiedat",
    "verifiedby",
    "reviewedat",
    "reviewedby",
    "createdby",
    "createdbyname",
    "lastmodifiedby",
    "lastmodifiedbyname",
    "volunteercount",
}


def _changed_fields(details):
    match = re.search(r"Changed:\s*(.+?)(?:\.|$)", details or "", re.IGNORECASE)
    if not match:
        return []
    return [
        re.sub(r"[^a-z0-9]", "", value.casefold())
        for value in match.group(1).split(",")
        if value.strip()
    ]


def _has_primary_action(Log, entry):
    candidates = Log.objects.filter(
        admin_id=entry.admin_id,
        admin_name=entry.admin_name,
        section=entry.section,
        record_type=entry.record_type,
        record_id=entry.record_id,
        action__in=["create", "edit", "status", "approval"],
        created_at__gte=entry.created_at - timedelta(minutes=2),
        created_at__lte=entry.created_at + timedelta(minutes=2),
    ).exclude(pk=entry.pk)
    for candidate in candidates.only("action", "details").iterator():
        if candidate.action != "edit":
            return True
        candidate_fields = _changed_fields(candidate.details)
        if candidate_fields and not set(candidate_fields).issubset(SYSTEM_FIELD_NAMES):
            return True
    return False


def _remove_generated_field_edits(Log):
    redundant_ids = []
    for entry in Log.objects.filter(action="edit").only(
        "id", "admin_id", "admin_name", "section", "record_type", "record_id", "details", "created_at"
    ).iterator():
        fields = _changed_fields(entry.details)
        if not fields or not set(fields).issubset(SYSTEM_FIELD_NAMES):
            continue

        if _has_primary_action(Log, entry):
            redundant_ids.append(entry.pk)

    for start in range(0, len(redundant_ids), 500):
        Log.objects.filter(pk__in=redundant_ids[start:start + 500]).delete()


def _remove_exact_duplicates(Log):
    seen = {}
    duplicate_ids = []
    window = timedelta(seconds=2)
    for entry in Log.objects.order_by("created_at", "pk").iterator():
        key = (
            entry.admin_id,
            entry.admin_name,
            entry.section,
            entry.action,
            entry.record_type,
            entry.record_id,
            entry.record_label,
            entry.details,
        )
        prior = seen.get(key)
        if prior and entry.created_at - prior[0] <= window:
            duplicate_ids.append(entry.pk)
        else:
            seen[key] = (entry.created_at, entry.pk)

    for start in range(0, len(duplicate_ids), 500):
        Log.objects.filter(pk__in=duplicate_ids[start:start + 500]).delete()


def clean_admin_activity_log(apps, schema_editor):
    Log = apps.get_model("webapp", "AdminActivityLog")
    _remove_generated_field_edits(Log)
    _remove_exact_duplicates(Log)


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0073_merge_related_admin_activity_logs"),
    ]

    operations = [
        migrations.RunPython(clean_admin_activity_log, migrations.RunPython.noop),
    ]
