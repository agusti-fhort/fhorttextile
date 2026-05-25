from django.apps import AppConfig


class TasksConfig(AppConfig):
    name = 'fhort.tasks'

    def ready(self):
        import fhort.tasks.signals  # noqa
