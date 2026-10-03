from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0042_volunteercertificate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activity",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("draft", "Draft"),
                    ("cancelled", "Cancelled"),
                    ("completed", "Completed"),
                ],
                default="active",
                max_length=20,
            ),
        ),
    ]
