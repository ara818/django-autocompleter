from django import forms
from django.conf import settings
from django.db.models import ObjectDoesNotExist

from autocompleter import Autocompleter, registry


STATIC_PREFIX = '{static}autocompleter'.format(static=settings.STATIC_URL)


class AutocompleterWidget(forms.TextInput):
    """
    Renders an <input> element that handles search via the Autocompleter API.
    It passes the provided autocompleter URL to the element as data attributes,
    and makes sure that the corresponding JS & CSS is loaded.
    """
    class Media:
        js = ('{}/js/dj.autocompleter.js'.format(STATIC_PREFIX),)
        css = {
            'all': ('{}/css/dj.autocompleter.css'.format(STATIC_PREFIX),)
        }

    def __init__(self, autocompleter_url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.autocompleter_url = autocompleter_url

    def build_attrs(self, *args, **kwargs):
        """
        pass autocompleter values to jQuery via data-attributes
        """
        attrs = super().build_attrs(*args, **kwargs)
        attrs.update({
            'data-autocompleter': '',
            'data-autocompleter-url': self.autocompleter_url
        })
        return attrs


class AutocompleterSelectWidget(forms.MultiWidget):
    """
    This widget renders two adjacent <input> elements that provide a clean user interface
    for searching via the Autocompleter API & selecting the desired object.

    Wrapper for 2 widgets:
        1. `AutocompleterWidget`: renders an <input> that acts as the search field.
        2. `HiddenInput`: renders an <input> that holds the actual DB value (which is some kind of GUI)


    :autocompleter_name - `str` specify the Autocompleter to use for search.
    :display_name_field - `str` specify field from payload to display to user when result is selected.
    :database_field     - `str` specify field from payload to save to the DB (should be a GUI).
    :object_resolver    - `callable` that can fetch the object using the `database_field` value.
    """

    def __init__(self, autocompleter_name, autocompleter_url, display_name_field,
                 database_field, object_resolver=None, *args, **kwargs):
        self.autocompleter_name = autocompleter_name
        self.display_name_field = display_name_field
        self.database_field = database_field
        self.object_resolver = object_resolver

        widgets = [
            AutocompleterWidget(autocompleter_url),
            forms.HiddenInput()
        ]
        super().__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        """
        Decompress the field's DB value to both widgets <input> fields.

            1. since `value` is the object identifier, we do a reverse lookup to fetch the AC
               payload and show the `display_name_field` value.
            2. `value` is held in the `HiddenInput` as the DB value.

        returns [`display_name_field`, `db_value`]
        """
        # if DB field is empty, keep widgets blank.
        if not value:
            return [None, None]

        # if no `object_resolver` callable is provided, we can fall back to showing
        # the DB value in the search field. Not ideal, but better than leaving it blank.
        if not self.object_resolver:
            return ['ID: {}'.format(value), value]

        # use the `object_resolver` to fetch the object instance.
        try:
            obj = self.object_resolver(value)
        except ObjectDoesNotExist:
            return ['Object does not exit', value]

        # Use the `obj` and the Autocompleter to find the `ModelProvider`.
        model_provider = self._get_model_provider(obj)
        # with the provider & object_id, we can do a direct lookup for the AC payload.
        object_data = Autocompleter(self.autocompleter_name).get_provider_result_from_id(
            provider_name=model_provider.provider_name,
            object_id=model_provider(obj).get_item_id()
        )
        # show the `display_name_field` value in the search field.
        name = object_data.get(self.display_name_field)
        return [name, value]

    def _get_model_provider(self, obj):
        """
        Fetch the `AutocompleterModelProvider` class for a specific model from the registry.

        Note: because there is no guarantee that a provider is unique per Autocompleter
        or per model_class alone, we take the intersection of both result sets.
        """
        providers_by_ac = set(registry.get_all_by_autocompleter(self.autocompleter_name))
        model_providers = set(registry.get_all_by_model(obj.__class__))
        try:
            model_provider = providers_by_ac.intersection(model_providers).pop()
        except KeyError:
            model_provider = None
        return model_provider
