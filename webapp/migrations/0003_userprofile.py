import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import webapp.models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0002_rename_webapp_mate_user_id_7403cd_idx_webapp_mate_user_id_f1e291_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("avatar", models.ImageField(blank=True, null=True, upload_to=webapp.models.user_avatar_upload_to)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("birthdate", models.DateField(blank=True, null=True)),
                ("civil_status", models.CharField(blank=True, max_length=30)),
                ("address_line", models.CharField(blank=True, max_length=255)),
                ("barangay", models.CharField(blank=True, max_length=120)),
                ("city_municipality", models.CharField(blank=True, max_length=120)),
                ("emergency_contact_name", models.CharField(blank=True, max_length=150)),
                ("emergency_contact_relationship", models.CharField(blank=True, max_length=80)),
                ("emergency_contact_phone", models.CharField(blank=True, max_length=50)),
                ("volunteer_role", models.CharField(blank=True, max_length=80)),
                ("assigned_chapter_area", models.CharField(blank=True, max_length=150)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="userprofile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
