from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0079_skilllearningprogressaudit"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="beneficiary_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("happy_kids", "Happy Kids"),
                    ("happy_nannies", "Happy Nannies"),
                    ("happy_hearts", "Happy Hearts"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="linked_parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="linked_beneficiaries",
                to="webapp.userprofile",
            ),
        ),
    ]