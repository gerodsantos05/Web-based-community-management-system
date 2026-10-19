from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0076_volunteeractivityphoto"),
    ]

    operations = [
        migrations.AddField(
            model_name="volunteeractivityphoto",
            name="caption",
            field=models.CharField(blank=True, max_length=300),
        ),
    ]