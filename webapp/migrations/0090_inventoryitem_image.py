from django.db import migrations, models
import webapp.models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0089_skilllearningtopic_created_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventoryitem",
            name="image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=webapp.models.inventory_product_image_upload_to,
            ),
        ),
    ]
