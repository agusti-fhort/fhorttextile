from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'fhort.accounts'

    def ready(self):
        from . import signals  # noqa: F401
