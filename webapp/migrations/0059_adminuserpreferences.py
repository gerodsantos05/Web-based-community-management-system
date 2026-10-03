from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


UI_PREFERENCE_KEYS = ("pref_dark_mode", "pref_animations", "font_size", "font_type")


def move_shared_preferences_to_admins(apps, schema_editor):
    database = schema_editor.connection.alias
    system_settings_model = apps.get_model("webapp", "AdminSystemSettings")
    preferences_model = apps.get_model("webapp", "AdminUserPreferences")
    user_model_name, user_model_class = settings.AUTH_USER_MODEL.split(".")
    user_model = apps.get_model(user_model_name, user_model_class)

    system_settings = system_settings_model.objects.using(database).filter(pk="global").first()
    if not system_settings or not isinstance(system_settings.settings, dict):
        return

    preferences = {
        key: system_settings.settings[key]
        for key in UI_PREFERENCE_KEYS
        if key in system_settings.settings
    }
    if not preferences:
        return

    admin_ids = user_model.objects.using(database).filter(is_superuser=True).values_list("pk", flat=True)
    for user_id in admin_ids.iterator():
        preferences_model.objects.using(database).get_or_create(
            user_id=user_id,
            defaults={"preferences": preferences},
        )

    system_settings.settings = {
        key: value for key, value in system_settings.settings.items()
        if key not in UI_PREFERENCE_KEYS
    }
    system_settings.save(using=database, update_fields=["settings", "updated_at"])


def restore_shared_preferences(apps, schema_editor):
    database = schema_editor.connection.alias
    system_settings_model = apps.get_model("webapp", "AdminSystemSettings")
    preferences_model = apps.get_model("webapp", "AdminUserPreferences")
    system_settings = system_settings_model.objects.using(database).filter(pk="global").first()
    first_preferences = preferences_model.objects.using(database).order_by("user_id").first()
    if not system_settings or not first_preferences or not isinstance(first_preferences.preferences, dict):
        return

    settings_values = system_settings.settings if isinstance(system_settings.settings, dict) else {}
    settings_values.update(first_preferences.preferences)
    system_settings.settings = settings_values
    system_settings.save(using=database, update_fields=["settings", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("webapp", "0058_adminsystemsettings_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminUserPreferences",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("preferences", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="admin_ui_preferences", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(move_shared_preferences_to_admins, restore_shared_preferences),
    ]