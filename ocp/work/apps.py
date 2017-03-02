from django.apps import AppConfig


class WorkAppConfig(AppConfig):
    name = 'ocp.work'
    verbose_name = 'Work'

    def ready(self):
        import ocp.work.signals
