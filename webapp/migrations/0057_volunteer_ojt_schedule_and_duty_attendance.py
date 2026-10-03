from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def _attendance_target_constraint():
    condition = models.Q(assignment__isnull=False) | models.Q(duty_date__isnull=False)
    argument = "condition" if DJANGO_VERSION >= (5, 1) else "check"
    return models.CheckConstraint(**{argument: condition, "name": "vol_attendance_target"})


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("webapp", "0056_resourcelibrarymaterial_custom_category_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="VolunteerOjtSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_from", models.DateField()),
                ("effective_until", models.DateField(blank=True, null=True)),
                ("weekdays", models.JSONField(blank=True, default=list)),
                ("daily_times", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("volunteer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ojt_schedules", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["effective_from", "id"]},
        ),
        migrations.AlterField(
            model_name="volunteerattendancerecord",
            name="assignment",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="attendance_records", to="webapp.volunteeractivityassignment"),
        ),
        migrations.AddField(
            model_name="volunteerattendancerecord",
            name="duty_schedule",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="attendance_records", to="webapp.volunteerojtschedule"),
        ),
        migrations.AddField(
            model_name="volunteerattendancerecord",
            name="duty_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="volunteerattendancerecord",
            name="auto_closed",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="volunteerattendancerecord",
            name="status",
            field=models.CharField(choices=[("active", "Active"), ("pending", "Pending"), ("confirmed", "Confirmed"), ("rejected", "Rejected")], default="pending", max_length=20),
        ),
        migrations.AddConstraint(
            model_name="volunteerojtschedule",
            constraint=models.UniqueConstraint(fields=("volunteer", "effective_from"), name="uniq_vol_ojt_start"),
        ),
        migrations.AddConstraint(
            model_name="volunteerattendancerecord",
            constraint=_attendance_target_constraint(),
        ),
        migrations.AddConstraint(
            model_name="volunteerattendancerecord",
            constraint=models.UniqueConstraint(condition=models.Q(("duty_date__isnull", False)), fields=("volunteer", "duty_date"), name="uniq_vol_duty_date"),
        ),
    ]