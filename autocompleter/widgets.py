from collections import OrderedDict

from django import forms
from django.conf import settings

from autocompleter import Autocompleter


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
        2. `HiddenInput`: renders an <input> that holds the actual object ID / `search_id` value.
    """

    def __init__(self, autocompleter_name, autocompleter_url, display_name_field, *args, **kwargs):
        self.autocompleter_name = autocompleter_name
        self.display_name_field = display_name_field
        widgets = [
            AutocompleterWidget(autocompleter_url),
            forms.HiddenInput()
        ]
        super().__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        """
        Decompress the field's DB value to both widgets.
            1. `value` being the identifier, it goes to the `HiddenInput`.
            2. using the identifier, we load the corresponding display name (or search term). The best way
               to do so is by taking the first result from the `Autocompleter.exact_suggest`;
               since we are using the object's unique identifier, `exact_suggest` should yield only 1 result.

        If the field is empty, leave both values blank (None).
        """
        if value:
            result = Autocompleter(self.autocompleter_name).exact_suggest(value)
            try:
                if type(result) in (OrderedDict, dict):
                    # in the case of multiple providers, flatten our result set
                    # to the first non-empty container and pick out the first value.
                    ac_result = next(filter(None, result.values()))
                    exact_match = ac_result[0]
                else:
                    # otherwise, simply take the first result from our container.
                    exact_match = result[0]
                name = exact_match.get(self.display_name_field)
            except (StopIteration, IndexError, KeyError):
                name = None
            return [name, value]

        return [None, None]
