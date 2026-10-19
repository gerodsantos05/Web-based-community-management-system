from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0083_roleapplication_applicant_added_details"),
    ]

    operations = [
        migrations.AddField(
            model_name="roleapplication",
            name="applicant_details_consent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="roleapplication",
            name="applicant_details_consented_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]