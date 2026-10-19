import webapp.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0075_userprofile_volunteer_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VolunteerActivityPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to=webapp.models.volunteer_activity_photo_upload_to)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("assignment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="photos", to="webapp.volunteeractivityassignment")),
                ("volunteer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activity_photos", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-uploaded_at", "-id"],
            },
        ),
    ]