import re

from django.db import migrations, models
from django.db.models import Q


def correct_saved_program_names(apps, schema_editor):
    UserProfile = apps.get_model("webapp", "UserProfile")
    RoleApplication = apps.get_model("webapp", "RoleApplication")
    AdminActivityLog = apps.get_model("webapp", "AdminActivityLog")

    UserProfile.objects.filter(beneficiary_type="happy_nannies").update(beneficiary_type="happy_nanays")
    RoleApplication.objects.filter(track="happy_nannies").update(track="happy_nanas")
    entries = AdminActivityLog.objects.filter(
        Q(details__icontains="nannies") | Q(record_label__icontains="nannies")
    )
    for entry in entries.iterator():
        corrected_details = re.sub(r"happy nannies", "Happy Nanays", entry.details, flags=re.IGNORECASE)
        corrected_label = re.sub(r"happy nannies", "Happy Nanays", entry.record_label, flags=re.IGNORECASE)
        if corrected_details != entry.details or corrected_label != entry.record_label:
            entry.details = corrected_details
            entry.record_label = corrected_label
            entry.save(update_fields=["details", "record_label"])


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0086_roleapplication_happy_hearts_track"),
    ]

    operations = [
        migrations.RunPython(correct_saved_program_names, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="roleapplication",
            name="track",
            field=models.CharField(
                blank=True,
                choices=[
                    ("happy_nanas", "Happy Nanays"),
                    ("happy_kids", "Happy Kid's"),
                    ("happy_hearts", "Happy Hearts"),
                    ("intern", "OJT"),
                    ("community_volunteer", "Community"),
                ],
                max_length=30,
            ),
        ),
    ]