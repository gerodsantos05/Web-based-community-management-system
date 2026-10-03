from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0053_beneficiaryactivityattendance"),
    ]

    operations = [
        migrations.AddField(
            model_name="beneficiaryactivityattendance",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="beneficiaryactivityattendance",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_beneficiary_attendance",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
