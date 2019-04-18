from django.apps import AppConfig as BaseAppConfig
from django.utils.importlib import import_module


class AppConfig(BaseAppConfig):

    name = "djangoProject"

    def ready(self):
        import_module("djangoProject.receivers")
