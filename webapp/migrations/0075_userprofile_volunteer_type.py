from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0074_dedupe_admin_activity_log_side_effects"),
    ]

    operations = [
        migrations.AlterField(
            model_name="roleapplication",
            name="track",
            field=models.CharField(
                blank=True,
                choices=[
                    ("happy_nanas", "Happy Nanay's"),
                    ("happy_kids", "Happy Kid's"),
                    ("intern", "OJT"),
                    ("community_volunteer", "Community"),
                ],
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="volunteer_type",
            field=models.CharField(
                choices=[("ojt", "OJT"), ("community", "Community")],
                default="ojt",
                max_length=16,
            ),
        ),
    ]