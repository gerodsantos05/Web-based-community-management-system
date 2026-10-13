from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("webapp", "0071_activity_modifier"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminActivityLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("admin_name", models.CharField(max_length=150)),
                ("action", models.CharField(choices=[("create", "Added"), ("edit", "Edited"), ("delete", "Deleted"), ("status", "Status changed"), ("approval", "Approved or rejected")], max_length=12)),
                ("section", models.CharField(choices=[("Donations", "Donations"), ("Payments", "Payments"), ("Users", "Users"), ("Volunteers", "Volunteers"), ("Beneficiaries", "Beneficiaries"), ("Activities", "Activities"), ("Inventory", "Inventory")], max_length=24)),
                ("record_type", models.CharField(max_length=120)),
                ("record_id", models.CharField(max_length=64)),
                ("record_label", models.CharField(max_length=255)),
                ("details", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("admin", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activity_log_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["-created_at", "-id"], name="admin_log_created_idx"),
                    models.Index(fields=["section", "action"], name="admin_log_section_action_idx"),
                    models.Index(fields=["admin_name"], name="admin_log_admin_idx"),
                ],
            },
        ),
    ]