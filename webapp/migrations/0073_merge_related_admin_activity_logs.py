from datetime import timedelta
import re

from django.conf import settings
from django.db import migrations


LINKED_RECORD_TYPES = {
    "user profile",
    "role application",
    "activity fund allocation",
    "activity beneficiary assignment",
    "volunteer activity assignment",
    "stock movement",
    "volunteer attendance record",
    "volunteer certificate",
    "volunteer ojt schedule",
    "volunteer admin message",
    "volunteer admin message attachment",
    "beneficiary assistance record",
    "beneficiary assistance feedback",
    "beneficiary activity attendance",
    "beneficiary activity feedback",
}

LINKED_PARENT_TYPES = {
    "user profile": "user",
    "role application": "user",
    "activity fund allocation": "activity",
    "activity beneficiary assignment": "activity",
    "volunteer activity assignment": "activity",
    "stock movement": "inventory item",
    "volunteer attendance record": "volunteer",
    "volunteer certificate": "volunteer",
    "volunteer ojt schedule": "volunteer",
    "volunteer admin message": "volunteer",
    "volunteer admin message attachment": "volunteer",
    "beneficiary assistance record": "beneficiary",
    "beneficiary assistance feedback": "beneficiary",
    "beneficiary activity attendance": "beneficiary",
    "beneficiary activity feedback": "beneficiary",
    "user": "user",
    "volunteer": "volunteer",
    "beneficiary": "beneficiary",
    "activity": "activity",
    "inventory item": "inventory item",
}


def merge_related_entries(apps, schema_editor):
    Log = apps.get_model("webapp", "AdminActivityLog")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("webapp", "UserProfile")
    RoleApplication = apps.get_model("webapp", "RoleApplication")
    Activity = apps.get_model("webapp", "Activity")
    ActivityFundAllocation = apps.get_model("webapp", "ActivityFundAllocation")
    ActivityBeneficiaryAssignment = apps.get_model("webapp", "ActivityBeneficiaryAssignment")
    VolunteerActivityAssignment = apps.get_model("webapp", "VolunteerActivityAssignment")
    InventoryItem = apps.get_model("webapp", "InventoryItem")
    StockMovement = apps.get_model("webapp", "StockMovement")
    VolunteerAttendanceRecord = apps.get_model("webapp", "VolunteerAttendanceRecord")
    VolunteerCertificate = apps.get_model("webapp", "VolunteerCertificate")
    VolunteerOjtSchedule = apps.get_model("webapp", "VolunteerOjtSchedule")
    VolunteerAdminMessage = apps.get_model("webapp", "VolunteerAdminMessage")
    VolunteerAdminMessageAttachment = apps.get_model("webapp", "VolunteerAdminMessageAttachment")
    BeneficiaryAssistanceRecord = apps.get_model("webapp", "BeneficiaryAssistanceRecord")
    BeneficiaryAssistanceFeedback = apps.get_model("webapp", "BeneficiaryAssistanceFeedback")
    BeneficiaryActivityAttendance = apps.get_model("webapp", "BeneficiaryActivityAttendance")
    BeneficiaryActivityFeedback = apps.get_model("webapp", "BeneficiaryActivityFeedback")

    profiles = {
        pk: (user_id, role)
        for pk, user_id, role in UserProfile.objects.values_list("pk", "user_id", "account_role")
    }
    applications = {
        pk: (user_id, role, full_name)
        for pk, user_id, role, full_name in RoleApplication.objects.values_list("pk", "user_id", "role", "full_name")
    }
    activities = dict(Activity.objects.values_list("pk", "title"))
    activity_allocations = dict(ActivityFundAllocation.objects.values_list("pk", "activity_id"))
    activity_beneficiaries = dict(ActivityBeneficiaryAssignment.objects.values_list("pk", "activity_id"))
    volunteer_assignments = dict(VolunteerActivityAssignment.objects.values_list("pk", "activity_id"))
    inventory_items = dict(InventoryItem.objects.values_list("pk", "name"))
    stock_movements = dict(StockMovement.objects.values_list("pk", "item_id"))
    volunteer_attendance = dict(VolunteerAttendanceRecord.objects.values_list("pk", "volunteer_id"))
    volunteer_certificates = dict(VolunteerCertificate.objects.values_list("pk", "volunteer_id"))
    volunteer_schedules = dict(VolunteerOjtSchedule.objects.values_list("pk", "volunteer_id"))
    volunteer_messages = dict(VolunteerAdminMessage.objects.values_list("pk", "thread_user_id"))
    volunteer_attachments = dict(VolunteerAdminMessageAttachment.objects.values_list("pk", "message_id"))
    assistance_records = dict(BeneficiaryAssistanceRecord.objects.values_list("pk", "beneficiary_id"))
    assistance_feedback = dict(BeneficiaryAssistanceFeedback.objects.values_list("pk", "user_id"))
    beneficiary_attendance = dict(BeneficiaryActivityAttendance.objects.values_list("pk", "beneficiary_id"))
    beneficiary_feedback = dict(BeneficiaryActivityFeedback.objects.values_list("pk", "user_id"))
    user_names = {
        pk: (f"{first_name} {last_name}".strip() or username)
        for pk, first_name, last_name, username in User.objects.values_list("pk", "first_name", "last_name", "username")
    }

    def user_section(user_id):
        role = next((profile_role for profile_user, profile_role in profiles.values() if profile_user == user_id), None)
        if role is None:
            role = next((app_role for app_user, app_role, _name in applications.values() if app_user == user_id), None)
        return "Volunteers" if role == "volunteer" else "Beneficiaries" if role == "beneficiary" else "Users"

    def target_for(entry):
        kind = entry.record_type.strip().casefold()
        try:
            record_id = int(entry.record_id)
        except (TypeError, ValueError):
            return (kind, entry.record_id), entry.section, entry.record_type, entry.record_id, entry.record_label

        if kind == "user":
            section = user_section(record_id)
            record_type = "Volunteer" if section == "Volunteers" else "Beneficiary" if section == "Beneficiaries" else "User"
            return ("user", record_id), section, record_type, str(record_id), user_names.get(record_id, entry.record_label)
        if kind == "user profile" and record_id in profiles:
            user_id = profiles[record_id][0]
            section = user_section(user_id)
            record_type = "Volunteer" if section == "Volunteers" else "Beneficiary" if section == "Beneficiaries" else "User"
            return ("user", user_id), section, record_type, str(user_id), user_names.get(user_id, entry.record_label)
        if kind == "role application" and record_id in applications:
            user_id, role, full_name = applications[record_id]
            if user_id:
                section = "Volunteers" if role == "volunteer" else "Beneficiaries"
                record_type = "Volunteer" if role == "volunteer" else "Beneficiary"
                return ("user", user_id), section, record_type, str(user_id), user_names.get(user_id, full_name)
            return (kind, record_id), entry.section, entry.record_type, str(record_id), full_name
        if kind == "activity" or kind == "activity fund allocation" and record_id in activity_allocations:
            activity_id = record_id if kind == "activity" else activity_allocations[record_id]
            return ("activity", activity_id), "Activities", "Activity", str(activity_id), activities.get(activity_id, entry.record_label)
        if kind == "activity beneficiary assignment" and record_id in activity_beneficiaries:
            activity_id = activity_beneficiaries[record_id]
            return ("activity", activity_id), "Activities", "Activity", str(activity_id), activities.get(activity_id, entry.record_label)
        if kind == "volunteer activity assignment" and record_id in volunteer_assignments:
            activity_id = volunteer_assignments[record_id]
            if activity_id:
                return ("activity", activity_id), "Activities", "Activity", str(activity_id), activities.get(activity_id, entry.record_label)
        if kind == "inventory item":
            return ("inventory", record_id), "Inventory", "Inventory Item", str(record_id), inventory_items.get(record_id, entry.record_label)
        if kind == "stock movement" and record_id in stock_movements:
            item_id = stock_movements[record_id]
            return ("inventory", item_id), "Inventory", "Inventory Item", str(item_id), inventory_items.get(item_id, entry.record_label)

        related_user_id = None
        related_user_id = {
            "volunteer attendance record": volunteer_attendance.get(record_id),
            "volunteer certificate": volunteer_certificates.get(record_id),
            "volunteer ojt schedule": volunteer_schedules.get(record_id),
            "volunteer admin message": volunteer_messages.get(record_id),
            "beneficiary assistance feedback": assistance_feedback.get(record_id),
            "beneficiary activity attendance": beneficiary_attendance.get(record_id),
            "beneficiary activity feedback": beneficiary_feedback.get(record_id),
        }.get(kind)
        if kind == "volunteer admin message attachment" and record_id in volunteer_attachments:
            related_user_id = volunteer_messages.get(volunteer_attachments[record_id])
        if kind == "beneficiary assistance record" and record_id in assistance_records:
            application_id = assistance_records[record_id]
            related_user_id = applications.get(application_id, (None, None, None))[0]
        if related_user_id:
            section = user_section(related_user_id)
            record_type = "Volunteer" if section == "Volunteers" else "Beneficiary" if section == "Beneficiaries" else "User"
            return ("user", related_user_id), section, record_type, str(related_user_id), user_names.get(related_user_id, entry.record_label)
        return (kind, record_id), entry.section, entry.record_type, str(record_id), entry.record_label

    groups = {}
    window = timedelta(seconds=2)
    for entry in Log.objects.order_by("created_at", "pk").iterator():
        identity, section, record_type, record_id, label = target_for(entry)
        actor_key = entry.admin_id if entry.admin_id is not None else entry.admin_name
        key = (actor_key, identity)
        candidates = groups.setdefault(key, [])
        entry_type = entry.record_type.strip().casefold()
        entry_parent_type = LINKED_PARENT_TYPES.get(entry_type)
        match = next((
            group for group in reversed(candidates)
            if entry.created_at - group["last_created_at"] <= window
            and entry_parent_type
            and any(LINKED_PARENT_TYPES.get(existing_type) == entry_parent_type for existing_type in group["types"])
        ), None)
        if match is None:
            candidates.append({
                "entries": [entry],
                "types": {entry_type},
                "identity": identity,
                "section": section,
                "record_type": record_type,
                "record_id": record_id,
                "label": label,
                "last_created_at": entry.created_at,
            })
        else:
            match["entries"].append(entry)
            match["types"].add(entry_type)
            match["last_created_at"] = entry.created_at
            if section in {"Volunteers", "Beneficiaries"}:
                match["section"] = section
                match["record_type"] = record_type
            if len(label) > len(match["label"]):
                match["label"] = label

    action_priority = {"edit": 0, "status": 1, "create": 2, "approval": 3, "delete": 4}
    for candidates in groups.values():
        for group in candidates:
            if len(group["entries"]) < 2:
                continue
            entries = group["entries"]
            action = max(entries, key=lambda item: action_priority.get(item.action, 0)).action
            changed_fields = []
            status_details = []
            other_details = []
            for item in entries:
                detail = item.details.strip()
                match = re.search(r"Changed:\s*(.+?)(?:\.|$)", detail)
                if match:
                    changed_fields.extend(value.strip() for value in match.group(1).split(",") if value.strip())
                status_match = re.search(r"Changed\s+(.+?)\s+to\s+(.+?)\s+for\s+.+?\.?$", detail)
                if status_match:
                    status_details.append(f"Status: {status_match.group(1)} → {status_match.group(2)}")
                elif item.action == "approval":
                    other_details.append(detail.split(" ", 1)[0].rstrip("."))
                elif detail and not detail.startswith(("Edited ", "Added ", "Deleted ")):
                    other_details.append(detail.rstrip("."))

            details = []
            for detail in status_details + other_details:
                if detail and detail not in details:
                    details.append(detail)
            fields = list(dict.fromkeys(changed_fields))
            if fields:
                details.append("Changed: " + ", ".join(fields))

            primary = min(entries, key=lambda item: (item.created_at, item.pk))
            primary.action = action
            primary.section = group["section"]
            primary.record_type = group["record_type"]
            primary.record_id = group["record_id"]
            primary.record_label = group["label"][:255]
            primary.details = "; ".join(details) or "Updated linked records."
            primary.save(update_fields=["action", "section", "record_type", "record_id", "record_label", "details"])
            Log.objects.filter(pk__in=[item.pk for item in entries if item.pk != primary.pk]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0072_admin_activity_log"),
    ]

    operations = [
        migrations.RunPython(merge_related_entries, migrations.RunPython.noop),
    ]
