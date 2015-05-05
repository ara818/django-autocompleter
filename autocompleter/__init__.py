VERSION = (0, 5, 1)

from autocompleter.registry import registry, signal_registry
from autocompleter.base import AutocompleterBase, AutocompleterModelProvider, AutocompleterDictProvider, Autocompleter

from django.utils.module_loading import autodiscover_modules

__all__ = [
    'registry', 'signal_registry', 'AutocompleterBase', 'AutocompleterModelProvider',
    'AutocompleterDictProvider', 'Autocompleter',
]


def autodiscover():
    """
    Auto-discover INSTALLED_APPS autocompleters.py modules and fail silently when
    not present.
    NOTE: autodiscover was copied from django.contrib.admin autodiscover
    """
    autodiscover_modules('autocompleters')

default_app_config = 'autocompleter.apps.AutocompleterConfig'
