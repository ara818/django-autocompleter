from django.apps import AppConfig


class SimpleAutocompleterConfig(AppConfig):
    """Simple AppConfig which does not do automatic discovery."""

    name = "autocompleter"
    verbose_name = "Autocompleter"


class AutocompleterConfig(SimpleAutocompleterConfig):
    """The default AppConfig for autocompleter which does autodiscovery."""

    def ready(self):
        self.module.autodiscover()
