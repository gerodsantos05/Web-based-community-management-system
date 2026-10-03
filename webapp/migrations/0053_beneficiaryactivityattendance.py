from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0052_alter_communitynotification_notification_type_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="beneficiaryactivityattendance",
            name="unique_beneficiary_activity_attendance",
        ),
        migrations.AddField(
            model_name="beneficiaryactivityattendance",
            name="volunteer",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="beneficiary_attendance_confirmations", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="beneficiaryactivityattendance",
            name="status",
            field=models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("rejected", "Rejected")], default="pending", max_length=20),
        ),
        migrations.AddField(
            model_name="beneficiaryactivityattendance",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="beneficiaryactivityattendance",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="beneficiaryactivityattendance",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="beneficiaryactivityattendance",
            name="confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name="beneficiaryactivityattendance",
            options={"ordering": ["-confirmed_at", "-created_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="beneficiaryactivityattendance",
            constraint=models.UniqueConstraint(fields=("activity", "beneficiary", "volunteer"), name="unique_activity_beneficiary_volunteer_attendance"),
        ),
    ]
