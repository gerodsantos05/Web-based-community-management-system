from django.db import migrations, models


def migrate_happy_nannies_to_nanays(apps, schema_editor):
    UserProfile = apps.get_model("webapp", "UserProfile")
    UserProfile.objects.filter(beneficiary_type="happy_nannies").update(beneficiary_type="happy_nanays")


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0080_userprofile_beneficiary_type_linked_parent"),
    ]

    operations = [
        migrations.RunPython(migrate_happy_nannies_to_nanays, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="userprofile",
            name="beneficiary_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("happy_kids", "Happy Kids"),
                    ("happy_nanays", "Happy Nanays"),
                    ("happy_hearts", "Happy Hearts"),
                ],
                default="",
                max_length=20,
            ),
        ),
    ]