VERSION = (0, 3, 0)

from autocompleter.registry import registry, signal_registry
from autocompleter.base import AutocompleterBase, AutocompleterProvider, Autocompleter

LOADING_AUTOCOMPELTER = False


def autodiscover():
    """
    Auto-discover INSTALLED_APPS autocompleters.py modules and fail silently when
    not present.
    NOTE: autodiscover was copied from django.contrib.admin autodiscover
    """
    global LOADING_AUTOCOMPELTER
    if LOADING_AUTOCOMPELTER:
        return
    LOADING_AUTOCOMPELTER = True

    import imp
    from django.utils.importlib import import_module
    from django.conf import settings

    for app in settings.INSTALLED_APPS:
        try:
            app_path = import_module(app).__path__
        except AttributeError:
            continue

        try:
            imp.find_module('models', app_path)
        except ImportError:
            continue

        import_module("%s.models" % app)

    LOADING_AUTOCOMPELTER = False
