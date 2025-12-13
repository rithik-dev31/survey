from django.apps import AppConfig


class AdministatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administator'

    def ready(self):
        import administator.signals 