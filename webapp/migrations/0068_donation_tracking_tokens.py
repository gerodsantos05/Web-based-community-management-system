from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0067_itempledge"),
    ]

    operations = [
        migrations.AddField(
            model_name="donation",
            name="tracking_token",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="itempledge",
            name="tracking_token",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
    ]
