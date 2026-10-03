from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		migrations.swappable_dependency(settings.AUTH_USER_MODEL),
		("webapp", "0031_communitypostreport_and_more"),
	]

	operations = [
		migrations.CreateModel(
			name="SkillLearningTopicEngagement",
			fields=[
				("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
				("page_open_count", models.PositiveIntegerField(default=0)),
				("last_accessed_at", models.DateTimeField(blank=True, null=True)),
				("topic", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="engagements", to="webapp.skilllearningtopic")),
				("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="skill_learning_topic_engagements", to=settings.AUTH_USER_MODEL)),
			],
			options={
				"constraints": [models.UniqueConstraint(fields=("user", "topic"), name="unique_skill_topic_user_engagement")],
			},
		),
		migrations.CreateModel(
			name="SkillLearningMaterialEngagement",
			fields=[
				("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
				("view_count", models.PositiveIntegerField(default=0)),
				("completed_at", models.DateTimeField(blank=True, null=True)),
				("last_accessed_at", models.DateTimeField(blank=True, null=True)),
				("material", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="engagements", to="webapp.skilllearningmaterial")),
				("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="skill_learning_material_engagements", to=settings.AUTH_USER_MODEL)),
			],
			options={
				"constraints": [models.UniqueConstraint(fields=("user", "material"), name="unique_skill_material_user_engagement")],
			},
		),
	]