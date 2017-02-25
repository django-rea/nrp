from django.apps import AppConfig


class ValueAccountingAppConfig(AppConfig):
    name = 'django_rea.valueaccounting'
    verbose_name = "Value Accounting"

    def ready(self):
        super(ValueAccountingAppConfig, self).ready()

        import django_rea.valueaccounting.signals