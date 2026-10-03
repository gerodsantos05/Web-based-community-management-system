from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import webapp.models


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0036_donation_impact_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="donation",
            name="receipt",
            field=models.FileField(blank=True, null=True, upload_to=webapp.models.donation_receipt_upload_to),
        ),
        migrations.AddField(
            model_name="donation",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="donation",
            name="verified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="verified_donations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
