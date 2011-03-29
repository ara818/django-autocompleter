from autocompleter import settings

class AutocompleterRegistry(object):
    
    def __init__(self):
        self._providers = {}
        
    def register_named(self, name, provider):
        """
        Register a model with a autocomplete provider.
        A model can have a list of providers that it uses for autocomplete.
        """
        if name not in self._providers:
            self._providers[name] = {}

        self._providers[name][provider.model] = provider

    def register(self, provider):
        """
        Register a model with the base autocomplete provider.
        """
        self.register_named(settings.DEFAULT_NAME, provider)
        
    def unregister_named(self, name, provider):
        """
        Urnegister a model with a autocomplete provider.
        """
        if model_class in self._providers:
            del(self._providers[name][provider.model])

    def unregister(self, provider):
        """
        Unregister a model with the base autocomplete provider.
        """
        self.unregister_named(settings.DEFAULT_NAME, provider)
    
    def get(self, name, model):
        if name not in self._providers:
            return None
        if model not in  self._providers[name]:
            return None
        return self._providers[name][model]

    def get_all(self, name):
        if name not in self._providers:
            return None
        return self._providers[name].values()

registry = AutocompleterRegistry()

