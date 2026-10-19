from django.db import migrations, models


def restore_happy_nanays_type(apps, schema_editor):
    UserProfile = apps.get_model("webapp", "UserProfile")
    AdminActivityLog = apps.get_model("webapp", "AdminActivityLog")

    for profile in UserProfile.objects.filter(beneficiary_type="happy_hearts").iterator():
        latest_type_log = (
            AdminActivityLog.objects
            .filter(
                section="Beneficiaries",
                record_id=str(profile.user_id),
                details__startswith="Type: ",
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if not latest_type_log:
            continue
        current_type = latest_type_log.details.rsplit(" -> ", 1)[-1].removeprefix("Type: ").strip()
        if current_type == "Happy Nannies":
            UserProfile.objects.filter(pk=profile.pk).update(beneficiary_type="happy_nanays")


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0081_beneficiary_type_happy_heart"),
    ]

    operations = [
        migrations.RunPython(restore_happy_nanays_type, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="userprofile",
            name="beneficiary_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("happy_nanays", "Happy Nanays"),
                    ("happy_kids", "Happy Kids"),
                    ("happy_hearts", "Happy Hearts"),
                ],
                default="",
                max_length=20,
            ),
        ),
    ]