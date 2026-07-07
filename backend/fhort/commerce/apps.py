from django.apps import AppConfig


class CommerceConfig(AppConfig):
    name = 'fhort.commerce'

    def ready(self):
        import fhort.commerce.signals  # noqa
