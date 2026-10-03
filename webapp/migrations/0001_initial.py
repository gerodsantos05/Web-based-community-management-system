import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import webapp.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialSubmission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("topic_id", models.CharField(max_length=120)),
                ("topic_title", models.CharField(blank=True, max_length=255)),
                ("material_id", models.CharField(max_length=120)),
                ("material_title", models.CharField(blank=True, max_length=255)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="material_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user", "topic_id", "material_id"], name="webapp_mate_user_id_7403cd_idx"),
                    models.Index(fields=["-created_at"], name="webapp_mate_created_dafc3b_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="MaterialSubmissionFile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file", models.FileField(upload_to=webapp.models.material_submission_upload_to)),
                ("original_name", models.CharField(max_length=255)),
                ("mime_type", models.CharField(blank=True, max_length=120)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="files",
                        to="webapp.materialsubmission",
                    ),
                ),
            ],
            options={
                "ordering": ["uploaded_at"],
            },
        ),
    ]
