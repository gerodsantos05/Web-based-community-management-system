from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0046_merge_20260923_ojt_profile_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activity",
            name="category",
            field=models.CharField(
                choices=[
                    ("rag-making", "Rag-making"),
                    ("teaching-kids", "Teaching Kids"),
                    ("pagtatanim", "Planting"),
                    ("outreach", "Outreach"),
                    ("other", "Other"),
                ],
                default="",
                max_length=120,
            ),
        ),
    ]
