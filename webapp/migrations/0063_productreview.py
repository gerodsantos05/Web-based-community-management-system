from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0062_roleapplication_track_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_name", models.CharField(max_length=150)),
                ("variation", models.CharField(blank=True, max_length=255)),
                ("rating", models.PositiveSmallIntegerField()),
                ("message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("inquiry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_reviews", to="webapp.productinquiry")),
            ],
            options={
                "indexes": [models.Index(fields=["product_name", "-created_at"], name="webapp_prod_product_4b66de_idx")],
                "constraints": [models.UniqueConstraint(fields=["inquiry", "product_name", "variation"], name="unique_product_review_per_order_item")],
            },
        ),
    ]
