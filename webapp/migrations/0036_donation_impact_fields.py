from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0035_rename_webapp_volu_volunte_attend_1_idx_webapp_volu_volunte_b8ccc1_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="donation",
            name="impact_update",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="donation",
            name="impact_update_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="communitynotification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("post_like", "Post like"),
                    ("post_comment", "Post comment"),
                    ("comment_reply", "Comment reply"),
                    ("role_application", "Role application"),
                    ("beneficiary_application_decision", "Beneficiary application decision"),
                    ("volunteer_application_decision", "Volunteer application decision"),
                    ("volunteer_assignment", "Volunteer assignment"),
                    ("donation_impact", "Donation impact update"),
                ],
                max_length=40,
            ),
        ),
    ]
