from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0013_alter_roleapplication_user"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BeneficiaryAssistanceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("aid_type", models.CharField(max_length=150)),
                ("quantity_or_amount", models.CharField(max_length=120)),
                ("assistance_date", models.DateField()),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_volunteer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="beneficiary_assistance_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "beneficiary",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assistance_records",
                        to="webapp.roleapplication",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recorded_beneficiary_assistance",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-assistance_date", "-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="beneficiaryassistancerecord",
            index=models.Index(fields=["beneficiary", "-assistance_date"], name="webapp_bene_benefic_0d7f2f_idx"),
        ),
        migrations.AddIndex(
            model_name="beneficiaryassistancerecord",
            index=models.Index(fields=["assigned_volunteer", "-assistance_date"], name="webapp_bene_assigned_0a3ae1_idx"),
        ),
    ]
