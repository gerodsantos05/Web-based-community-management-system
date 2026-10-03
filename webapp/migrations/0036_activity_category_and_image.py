from django.db import migrations, models

import webapp.models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0035_rename_webapp_volu_volunte_attend_1_idx_webapp_volu_volunte_b8ccc1_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activity",
            name="category",
            field=models.CharField(choices=[("rag-making", "Rag-making"), ("teaching-kids", "Teaching Kids"), ("pagtatanim", "Pagtatanim"), ("outreach", "Outreach"), ("other", "Other")], default="", max_length=120),
        ),
        migrations.AddField(
            model_name="activity",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to=webapp.models.activity_cover_upload_to),
        ),
    ]