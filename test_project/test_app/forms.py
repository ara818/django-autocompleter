from autocompleter.fields import AutocompleterDictProviderSelectField
from django import forms
# compatible with django 1.7 - 2.0
try:
    # django >= 1.10
    from django.urls import reverse_lazy
except ImportError:
    # django 1.7 - 1.9
    from django.core.urlresolvers import reverse_lazy

from test_app.models import CalcListItem


class CalcListItemForm(forms.ModelForm):
    calc_name = AutocompleterDictProviderSelectField(
        autocompleter_name='metric',
        autocompleter_url=reverse_lazy('suggest', kwargs=dict(name='metric')),
        display_name_field='display_name',
        database_field='id',
    )

    class Meta:
        model = CalcListItem
        fields = ('calc_name',)
