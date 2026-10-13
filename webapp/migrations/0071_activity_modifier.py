from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_activity_creators(apps, schema_editor):
    Activity = apps.get_model("webapp", "Activity")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    first_admin = User.objects.filter(is_superuser=True).order_by("id").first()

    for activity in Activity.objects.filter(created_by_name__in=["", "Unknown"]).iterator():
        creator = User.objects.filter(pk=activity.created_by_id).first() if activity.created_by_id else first_admin
        if creator:
            activity.created_by_id = activity.created_by_id or creator.pk
            activity.created_by_name = f"{creator.first_name} {creator.last_name}".strip() or creator.username
        else:
            activity.created_by_name = "System"
        activity.save(update_fields=["created_by", "created_by_name"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("webapp", "0070_activity_creator"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="last_modified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="last_modified_activities",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="last_modified_by_name",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.RunPython(backfill_activity_creators, migrations.RunPython.noop),
    ]