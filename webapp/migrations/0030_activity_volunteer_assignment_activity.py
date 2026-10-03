from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0029_merge_20260806_1330"),
    ]

    operations = [
        migrations.AddField(
            model_name="volunteeractivityassignment",
            name="activity",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="volunteer_assignments",
                to="webapp.activity",
            ),
        ),
    ]
