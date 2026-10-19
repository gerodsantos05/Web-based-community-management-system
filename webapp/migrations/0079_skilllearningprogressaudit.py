import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("webapp", "0078_userprofile_gender"),
    ]

    operations = [
        migrations.CreateModel(
            name="SkillLearningProgressAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_completed_at", models.DateTimeField(blank=True, null=True)),
                ("new_completed_at", models.DateTimeField(blank=True, null=True)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "beneficiary",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skill_learning_progress_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="skill_learning_progress_edits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "material",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progress_changes",
                        to="webapp.skilllearningmaterial",
                    ),
                ),
            ],
            options={
                "ordering": ["-changed_at", "-id"],
            },
        ),
    ]
