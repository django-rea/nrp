from django.apps import AppConfig


class ValueAccountingAppConfig(AppConfig):
    name = 'valuenetwork.valueaccounting'
    verbose_name = "Value Accounting"

    def ready(self):
        super(ValueAccountingAppConfig, self).ready()

        import valuenetwork.valueaccounting.signals

