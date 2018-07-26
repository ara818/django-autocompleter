from django import forms
from django.conf import settings

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
