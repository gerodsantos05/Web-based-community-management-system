from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0033_volunteer_attendance"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="category",
            field=models.CharField(
                choices=[
                    ("rag-making", "Rag-making"),
                    ("teaching-kids", "Teaching Kids"),
                    ("pagtatanim", "Pagtatanim"),
                    ("outreach", "Outreach"),
                ],
                default="",
                max_length=30,
            ),
        ),
    ]