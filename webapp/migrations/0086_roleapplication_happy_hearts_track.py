from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0085_roleapplicationdocument"),
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
                    ("happy_hearts", "Happy Hearts"),
                    ("intern", "OJT"),
                    ("community_volunteer", "Community"),
                ],
                max_length=30,
            ),
        ),
    ]