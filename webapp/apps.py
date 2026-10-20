from django.apps import AppConfig


class WebappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webapp'

    def ready(self):
        from .audit import register_audit_signals
        from .auth_signals import register_account_activation_signals

        register_audit_signals()
        register_account_activation_signals()
