from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import webapp.models


class Migration(migrations.Migration):

	dependencies = [
		("webapp", "0017_alter_roleapplication_status"),
	]

	operations = [
		migrations.CreateModel(
			name="Donation",
			fields=[
				("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
				("reference_number", models.CharField(max_length=32, unique=True)),
				("donor_name", models.CharField(blank=True, max_length=150)),
				("donor_message", models.TextField(blank=True)),
				("campaign", models.CharField(default="General Donation", max_length=150)),
				("amount", models.PositiveIntegerField(default=0)),
				("payment_method", models.CharField(choices=[("gcash", "GCash"), ("bank_transfer", "Bank Transfer"), ("cash", "Cash"), ("card", "Credit Card"), ("ewallet", "E-wallet")], max_length=20)),
				("receipt", models.ImageField(blank=True, null=True, upload_to=webapp.models.donation_receipt_upload_to)),
				("status", models.CharField(choices=[("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
				("review_notes", models.TextField(blank=True)),
				("created_at", models.DateTimeField(auto_now_add=True)),
				("updated_at", models.DateTimeField(auto_now=True)),
				("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="donations", to=settings.AUTH_USER_MODEL)),
			],
			options={
				"ordering": ["-created_at", "-id"],
			},
		),
		migrations.AddIndex(
			model_name="donation",
			index=models.Index(fields=["status", "-created_at"], name="don_status_created_idx"),
		),
		migrations.AddIndex(
			model_name="donation",
			index=models.Index(fields=["payment_method", "-created_at"], name="don_method_created_idx"),
		),
		migrations.AddIndex(
			model_name="donation",
			index=models.Index(fields=["-created_at"], name="don_created_idx"),
		),
	]