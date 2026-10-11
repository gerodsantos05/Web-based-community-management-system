from django.db import migrations, models


def migrate_verified_donations(apps, schema_editor):
    Donation = apps.get_model("webapp", "Donation")
    Donation.objects.filter(status="verified").update(status="completed")


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0063_productreview"),
    ]

    operations = [
        migrations.RunPython(migrate_verified_donations, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="donation",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("completed", "Completed"),
                    ("rejected", "Rejected"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
