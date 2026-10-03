from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0044_userprofile_required_ojt_hours"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="ojt_supervisor",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="ojt_program",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="ojt_next_check_in",
            field=models.DateField(blank=True, null=True),
        ),
    ]
