from autocompleter import settings

class AutocompleterRegistry(object):
    
    def __init__(self):
        self._providers = {}

    def register(self, name='main', provider=None):
        """
        Register an autocompleter wit ha  provider. 
        Each autocompleter can have multiple providers.
        """
        if provider == None:
            return
        if name not in self._providers:
            self._providers[name] = {}

        self._providers[name][provider.model] = provider
        
    def unregister(self, name='main', provider=None):
        """
        Unregister a provider from the autocompleter.
        """
        if provider == None:
            return
        if model_class in self._providers:
            del(self._providers[name][provider.model])
    
    def get(self, name='main', model=None):
        if name not in self._providers:
            return None
        if model not in self._providers[name]:
            return None
        return self._providers[name][model]

    def get_all(self, name='main'):
        if name not in self._providers:
            return None
        return self._providers[name].values()

registry = AutocompleterRegistry()

