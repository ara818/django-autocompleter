from autocompleter.fields import AutocompleterDictProviderSelectField
from django import forms
from django.urls import reverse_lazy

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
