from django import forms
from autocompleter.widgets import AutocompleterDictProviderSelectWidget


class AutocompleterDictProviderSelectField(forms.CharField):
    """
    Django forms.CharField that implements the `AutocompleterSelectWidget`.
    """
    widget = AutocompleterDictProviderSelectWidget

    default_error_messages = {
        'invalid_choice': 'Select a valid choice. That choice is not one of the available choices.',
    }

    def __init__(self, autocompleter_name, autocompleter_url, display_name_field,
                 database_field, *args, **kwargs):
        kwargs['widget'] = self.widget(
            autocompleter_name, autocompleter_url, display_name_field, database_field,
        )
        super(AutocompleterDictProviderSelectField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """
        Essentially the reverse of `decompress` on the `AutocompleterSelectWidget`,
        i.e. `value` is a list of values, each corresponding to a widget, and we pick out
        the one we want to commit to the DB.
        In this case, the object identifier is from the HiddenInput, which is the 2nd value.
        """
        if not value:
            return None

        if not isinstance(value, list):
            data_field_value = value
        else:
            if len(value) != 2:
                raise forms.ValidationError(self.error_messages['invalid_choice'])
            else:
                data_field_value = value[1]

        return data_field_value
