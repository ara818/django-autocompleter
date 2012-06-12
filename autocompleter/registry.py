from autocompleter import settings

class AutocompleterRegistry(object):
    
    def __init__(self):
        self._providers_by_ac = {}
        self._providers_by_model = {}

    def register(self, name='main', provider=None):
        """
        Register an autocompleter wit ha  provider.
        Each autocompleter can have multiple providers.
        """
        if provider == None:
            return
        if name not in self._providers_by_ac:
            self._providers_by_ac[name] = {}
        if  provider.model not in self._providers_by_model:
            self._providers_by_model[provider.model] = {}

        self._providers_by_ac[name][provider.model] = provider
        self._providers_by_model[provider.model][name] = provider

    def unregister(self, name='main', provider=None):
        """
        Unregister a provider from the autocompleter.
        """
        if provider == None:
            return
        if name in self._providers_by_ac and \
            provider.model in self._providers_by_ac[name]:
            del self._providers_by_ac[name][provider.model]
        if provider.model in self._providers_by_model and \
            name in self._providers_by_model[provider.model]:
            del self._providers_by_model[name][provider.model]

    def get(self, name='main', model=None):
        if name not in self._providers_by_ac:
            return None
        if model not in self._providers_by_ac[name]:
            return None
        return self._providers_by_ac[name][model]

    def get_all_by_autocompleter(self, name='main'):
        if name not in self._providers_by_ac:
            return None
        return self._providers_by_ac[name].values()

    def get_all_by_model(self, model=None):
        if model == None:
            return None
        if model not in self._providers_by_model:
            return None
        return self._providers_by_model[model].values()

registry = AutocompleterRegistry()

