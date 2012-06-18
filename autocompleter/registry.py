from django.db.models.signals import post_save, pre_save, post_delete


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
            self._providers_by_model[provider.model] = []

        self._providers_by_ac[name][provider.model] = provider
        if provider not in self._providers_by_model[provider.model]:
            self._providers_by_model[provider.model].append(provider)

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
            provider in self._providers_by_model[provider.model]:
            self._providers_by_model[provider.model].remove(provider)

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
        return self._providers_by_model[model]


registry = AutocompleterRegistry()


def add_obj_to_autocompleter(sender, instance, created, **kwargs):
    if instance == None:
        return

    providers = registry.get_all_by_model(sender)
    for provider in providers:
        provider(instance).store()


def remove_old_obj_from_autocompleter(sender, instance, **kwargs):
    try:
        old_instance = sender.objects.get(pk=instance.pk)

        providers = registry.get_all_by_model(sender)
        for provider in providers:
            provider(old_instance).remove()
    except sender.DoesNotExist:
        return


def remove_obj_from_autocompleter(sender, instance, **kwargs):
    if instance == None:
        return

    providers = registry.get_all_by_model(sender)
    for provider in providers:
        provider(instance).remove()


class AutocompleterSignalRegistry(object):
    def register(self, model):
        post_save.connect(add_obj_to_autocompleter, sender=model,
            dispatch_uid='autocompleter.%s.add' % (model))
        pre_save.connect(remove_old_obj_from_autocompleter, sender=model,
            dispatch_uid='autocompleter.%s.remoe_old' % (model))
        post_delete.connect(remove_obj_from_autocompleter,
            sender=model, dispatch_uid='autocompleter.%s.remove' % (model))

    def unregister(self, model):
        post_save.disconnect(add_obj_to_autocompleter,
            sender=model, dispatch_uid='autocompleter.%s.add' % (model))
        pre_save.disconnect(remove_old_obj_from_autocompleter, sender=model,
            dispatch_uid='autocompleter.%s.remoe_old' % (model))
        post_delete.disconnect(remove_obj_from_autocompleter,
            sender=model, dispatch_uid='autocompleter.%s.remove' % (model))

signal_registry = AutocompleterSignalRegistry()
