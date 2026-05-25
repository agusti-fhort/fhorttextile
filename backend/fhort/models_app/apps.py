from django.apps import AppConfig


class ModelsAppConfig(AppConfig):
    name = 'fhort.models_app'

    def ready(self):
        import fhort.models_app.signals  # noqa
