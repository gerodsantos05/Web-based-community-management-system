from django.db import migrations, models
import django.db.models.deletion
import webapp.models


class Migration(migrations.Migration):
    dependencies = [("webapp", "0038_volunteeradminmessage_reply_edit")]
    operations = [migrations.CreateModel(
        name="VolunteerAdminMessageAttachment",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("file", models.FileField(upload_to=webapp.models.volunteer_admin_attachment_upload_to)),
            ("original_name", models.CharField(max_length=255)),
            ("mime_type", models.CharField(blank=True, max_length=120)),
            ("size_bytes", models.PositiveBigIntegerField(default=0)),
            ("message", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="attachment", to="webapp.volunteeradminmessage")),
        ],
    )]