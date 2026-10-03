import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import webapp.models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0004_userprofile_settings_state_communitypost"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CommunityPostAttachment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file", models.FileField(upload_to=webapp.models.community_post_attachment_upload_to)),
                ("original_name", models.CharField(max_length=255)),
                ("mime_type", models.CharField(blank=True, max_length=120)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="webapp.communitypost",
                    ),
                ),
            ],
            options={"ordering": ["uploaded_at"]},
        ),
    ]