from django.db import migrations, models
import webapp.models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0042_volunteercertificate"),
    ]

    operations = [
        migrations.AddField(
            model_name="volunteercertificate",
            name="pdf_file",
            field=models.FileField(blank=True, null=True, upload_to=webapp.models.volunteer_certificate_upload_to),
        ),
    ]
