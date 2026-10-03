# Generated manually for the new regular-user and role application flow.

from django.conf import settings
from django.db import migrations, models
from django.db.models import deletion


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0009_rename_webapp_comm_recipie_6caf8d_idx_webapp_comm_recipie_ae9240_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='account_role',
            field=models.CharField(choices=[('regular', 'Regular User'), ('beneficiary', 'Beneficiary'), ('volunteer', 'Volunteer')], default='regular', max_length=20),
        ),
        migrations.CreateModel(
            name='RoleApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('beneficiary', 'Beneficiary'), ('volunteer', 'Volunteer')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('full_name', models.CharField(max_length=150)),
                ('contact_details', models.TextField()),
                ('reason_for_assistance', models.TextField(blank=True)),
                ('supporting_information', models.TextField(blank=True)),
                ('skills', models.TextField(blank=True)),
                ('availability', models.TextField(blank=True)),
                ('areas_of_interest', models.TextField(blank=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('admin_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=deletion.SET_NULL, related_name='reviewed_role_applications', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=deletion.CASCADE, related_name='role_applications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at', '-id'],
                'indexes': [models.Index(fields=['user', 'role', 'status'], name='wa_role_usr_rl_st_idx'), models.Index(fields=['-created_at'], name='wa_role_crt_idx')],
            },
        ),
    ]