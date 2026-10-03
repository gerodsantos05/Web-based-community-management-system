from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0043_volunteercertificate_pdf_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="required_ojt_hours",
            field=models.DecimalField(decimal_places=2, default=80, max_digits=10),
        ),
    ]
