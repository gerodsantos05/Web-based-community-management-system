from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0016_rename_webapp_bene_benefic_0d7f2f_idx_webapp_bene_benefic_acd33a_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="roleapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("inactive", "Inactive"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]