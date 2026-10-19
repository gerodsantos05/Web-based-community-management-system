import django.db.models.deletion
import webapp.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0084_roleapplication_applicant_details_consent"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoleApplicationDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document_type", models.CharField(max_length=60)),
                ("file", models.FileField(storage=webapp.models.PrivateApplicationStorage(), upload_to=webapp.models.role_application_document_upload_to)),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=100)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="webapp.roleapplication")),
            ],
            options={"ordering": ["document_type", "id"]},
        ),
        migrations.AddConstraint(
            model_name="roleapplicationdocument",
            constraint=models.UniqueConstraint(fields=("application", "document_type"), name="uniq_role_app_document_type"),
        ),
    ]