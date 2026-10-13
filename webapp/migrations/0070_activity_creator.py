from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("webapp", "0069_alter_itempledge_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_activities",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="created_by_name",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
    ]