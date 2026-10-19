from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0077_volunteeractivityphoto_caption"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[
                    ("male", "Male"),
                    ("female", "Female"),
                    ("other", "Other"),
                    ("prefer_not", "Prefer not to say"),
                ],
                max_length=20,
            ),
        ),
    ]
