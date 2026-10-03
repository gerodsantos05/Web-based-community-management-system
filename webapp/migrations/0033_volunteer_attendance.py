from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("webapp", "0032_skill_learning_engagement"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="ojt_hours",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name="volunteeractivityassignment",
            name="status",
            field=models.CharField(
                choices=[
                    ("upcoming", "Upcoming"),
                    ("time_in", "Time In"),
                    ("in_progress", "In Progress"),
                    ("awaiting_confirmation", "Awaiting Confirmation"),
                    ("completed", "Completed"),
                    ("missed", "Missed"),
                    ("cancelled", "Cancelled"),
                    ("pending", "Pending"),
                ],
                default="pending",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="volunteeractivityassignment",
            name="attendance_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="volunteeractivityassignment",
            name="attendance_ended_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="VolunteerAttendanceRecord",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("time_in", models.DateTimeField(blank=True, null=True)),
                ("time_out", models.DateTimeField(blank=True, null=True)),
                ("duration_minutes", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attendance_records", to="webapp.volunteeractivityassignment")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_volunteer_attendance", to=settings.AUTH_USER_MODEL)),
                ("volunteer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="volunteer_attendance_records", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-time_out", "-time_in", "-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="volunteerattendancerecord",
            index=models.Index(fields=["volunteer", "status", "time_out"], name="webapp_volu_volunte_attend_1_idx"),
        ),
        migrations.AddIndex(
            model_name="volunteerattendancerecord",
            index=models.Index(fields=["assignment", "status"], name="webapp_volu_assignme_attend_1_idx"),
        ),
    ]