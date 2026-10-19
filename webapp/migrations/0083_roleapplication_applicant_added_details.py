from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0082_restore_happy_nanays_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="roleapplication",
            name="applicant_added_details",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]