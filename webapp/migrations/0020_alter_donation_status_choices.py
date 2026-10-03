from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		("webapp", "0019_merge_0018_activity_0018_donation"),
	]

	operations = [
		migrations.AlterField(
			model_name="donation",
			name="status",
			field=models.CharField(choices=[("pending", "Pending"), ("verified", "Verified"), ("completed", "Completed"), ("rejected", "Rejected"), ("cancelled", "Cancelled")], default="pending", max_length=20),
		),
	]