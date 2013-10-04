from django.db import models

from autocompleter import AutocompleterModelProvider, AutocompleterDictProvider, registry
from test_app import calc_info

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    market_cap = models.FloatField(null=True, blank=True)


class StockAutocompleteProvider(AutocompleterModelProvider):
    model = Stock
    provider_name = "stock"

    def get_terms(self):
        """
        Term is the name or symbol of the company.
        """
        return [self.obj.name, self.obj.symbol]

    def get_score(self):
        """
        Larger companies should end up higher in search results.
        """
        return self.obj.market_cap

    def get_data(self):
        return {
            'type': 'stock',
            'id': self.obj.id,
            'score': self.get_score(),
            'display_name': u'%s (%s)' % (self.obj.name, self.obj.symbol),
            'search_name': self.obj.symbol,
        }


class Indicator(models.Model):
    name = models.CharField(max_length=200, unique=True)
    internal_name = models.CharField(max_length=200, unique=True)
    score = models.FloatField(null=True, blank=True)


class IndicatorAutocompleteProvider(AutocompleterModelProvider):
    model = Indicator

    provider_name = "ind"

    def get_item_id(self):
        return self.obj.name

    def get_term(self):
        return self.obj.name

    def get_score(self):
        return self.obj.score

    def get_data(self):
        return {
            'type': 'indicator',
            'id': self.obj.id,
            'score': self.get_score(),
            'display_name': u'%s' % (self.obj.name,),
            'search_name': u'%s' % (self.obj.internal_name,),
        }


class IndicatorAliasedAutocompleteProvider(AutocompleterModelProvider):
    model = Indicator

    provider_name = "indal"

    def get_term(self):
        return self.obj.name

    def get_score(self):
        return self.obj.score

    def get_data(self):
        return {
            'type': 'indicator',
            'id': self.obj.id,
            'score': self.get_score(),
            'display_name': u'%s' % (self.obj.name,),
            'search_name': u'%s' % (self.obj.internal_name,),
        }

    @classmethod
    def get_phrase_aliases(self):
        return {
            'United States': ['US', 'USA', 'America', 'U-S-A', 'U/S-A'],
            'Consumer Price Index': 'CPI',
            'Gross Domestic Product': 'GDP',
            'California': 'CA',
            'Canada': 'CA',
        }

class IndicatorSelectiveAutocompleteProvider(AutocompleterModelProvider):
    model = Indicator

    provider_name = "indsel"
    settings = {}

    def get_term(self):
        return self.obj.name

    def get_score(self):
        return self.obj.score

    def get_data(self):
        return {
            'type': 'indicator',
            'id': self.obj.id,
            'score': self.get_score(),
            'display_name': u'%s' % (self.obj.name,),
            'search_name': u'%s' % (self.obj.internal_name,),
        }

    def include_item(self):
        if self.obj.name == 'US Unemployment Rate':
            return False
        return True


class CalcAutocompleteProvider(AutocompleterDictProvider):
    obj_dict = calc_info.calc_dicts
    model = 'metric'

    provider_name = "metric"
    settings = {}

    def get_item_id(self):
        return self.obj['label']

    def get_term(self):
        return self.obj['label']

    def get_score(self):
        return self.obj.get('score', 1)

    def get_data(self):
        return {
            'type': 'metric',
            'id': self.obj['label'],
            'score': self.obj.get('score', 1),
            'display_name': u'%s' % (self.obj['label'],),
            'search_name': u'%s' % (self.obj['label'],),
        }

    @classmethod
    def get_iterator(cls):
        return calc_info.calc_dicts


class CalcAliasedAutocompleteProvider(AutocompleterDictProvider):
    obj_dict = calc_info.calc_dicts
    model = 'metric_aliased'

    provider_name = "metric_aliased"
    settings = {}

    def get_item_id(self):
        return self.obj['label']

    def get_term(self):
        return self.obj['label']

    def get_score(self):
        return self.obj.get('score', 1)

    def get_data(self):
        return {
            'type': 'metric',
            'id': self.obj['label'],
            'score': self.obj.get('score', 1),
            'display_name': u'%s' % (self.obj['label'],),
            'search_name': u'%s' % (self.obj['label'],),
        }

    @classmethod
    def get_phrase_aliases(self):
        return {
        'EV': 'Enterprise Value',
        }

    @classmethod
    def get_one_way_phrase_aliases(self):
        return {
            'Revenue': 'Turnover',
        }

    @classmethod
    def get_iterator(cls):
        return calc_info.calc_dicts

registry.register("stock", StockAutocompleteProvider)
registry.register("mixed", StockAutocompleteProvider)
registry.register("mixed", IndicatorAutocompleteProvider)
registry.register("mixed", CalcAutocompleteProvider)
registry.register("indicator", IndicatorAutocompleteProvider)
registry.register("indicator_aliased", IndicatorAliasedAutocompleteProvider)
registry.register("indicator_selective", IndicatorSelectiveAutocompleteProvider)
registry.register("metric", CalcAutocompleteProvider)
registry.register("metric_aliased", CalcAliasedAutocompleteProvider)
