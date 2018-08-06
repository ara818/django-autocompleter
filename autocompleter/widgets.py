from django import forms
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from autocompleter import Autocompleter, AutocompleterDictProvider, registry


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

    def __init__(self, autocompleter_url, display_name_field, database_field, *args, **kwargs):
        super(AutocompleterWidget, self).__init__(*args, **kwargs)
        self.autocompleter_url = autocompleter_url
        self.display_name_field = display_name_field
        self.database_field = database_field

    def build_attrs(self, *args, **kwargs):
        """
        pass autocompleter values to jQuery via data-attributes
        """
        attrs = super(AutocompleterWidget, self).build_attrs(*args, **kwargs)
        attrs.update({
            'data-autocompleter': '',
            'data-autocompleter-url': self.autocompleter_url,
            'data-autocompleter-name-field': self.display_name_field,
            'data-autocompleter-db-field': self.database_field,
        })
        return attrs


class AutocompleterSelectWidgetBase(forms.MultiWidget):
    """
    This is a base class for a forms.Field widget that renders two adjacent <input> elements
    to provide a clean user interface for searching via the Autocompleter API.

    It is essentially a wrapper for 2 more granular widgets:
        1. `AutocompleterWidget`: renders an <input> that acts as the search field.
        2. `HiddenInput`: renders an <input> that holds the actual DB value (which is some kind of GUI)

    :autocompleter_name - `str` the Autocompleter used for search.
    :autocompleter_url  - `str` the search URL for the autocompleter API.
    :display_name_field - `str` field from payload to display to user when result is selected.
    :database_field     - `str` field from payload to save to the DB, serving as the obj identifier.
    """
    def __init__(self, autocompleter_name, autocompleter_url, display_name_field,
                 database_field, *args, **kwargs):
        self.autocompleter_name = autocompleter_name
        self.display_name_field = display_name_field
        self.database_field = database_field

        widgets = [
            AutocompleterWidget(autocompleter_url, display_name_field, database_field),
            forms.HiddenInput()
        ]
        super(AutocompleterSelectWidgetBase, self).__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        """
        Decompress the field's DB value to both widgets <input> fields.
        returns [`display_name_field`, `database_field`]
        """
        if not value:
            # if DB field is empty, return blank values.
            return [None, None]

        provider = self._get_provider()

        object_data = Autocompleter(self.autocompleter_name).get_provider_result_from_id(
            provider_name=provider.provider_name,
            object_id=self._get_object_id(value, provider)
        )
        if not object_data:
            raise forms.ValidationError('Unable to retrieve data for "{}"'.format(value))

        # show the `display_name_field` value in the search field.
        name = object_data.get(self.display_name_field)
        return [name, value]

    def _get_object_id(self, value, provider):
        raise NotImplementedError

    def _get_provider(self):
        raise NotImplementedError


class AutocompleterDictProviderSelectWidget(AutocompleterSelectWidgetBase):

    def _get_object_id(self, value, provider):
        """
        In the case of the `AutocompleterDictProvider`, the database_field value
        acts as the object identifier.
        """
        return value

    def _get_provider(self):
        providers = registry.get_all_by_autocompleter(self.autocompleter_name)
        if not providers or len(providers) != 1:
            raise ImproperlyConfigured('The Autocompleter used by the AutocompleterDictProviderSelectWidget '
                                       'must have only 1 provider.')
        provider = providers[0]
        if not issubclass(provider, AutocompleterDictProvider):
            raise ImproperlyConfigured('The Autocompleter used by the AutocompleterDictProviderSelectWidget '
                                       'must be of type `AutocompleterDictProvider`.')
        return provider
