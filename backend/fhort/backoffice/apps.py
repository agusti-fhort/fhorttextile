from django.apps import AppConfig


class BackofficeConfig(AppConfig):
    name = 'fhort.backoffice'

    def ready(self):
        from . import receivers   # noqa: F401  (registra el @receiver a l'arrencada)
