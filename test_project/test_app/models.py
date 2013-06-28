from django.db import models

from autocompleter import AutocompleterProvider, registry


class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    market_cap = models.FloatField(null=True, blank=True)


class StockAutocompleteProvider(AutocompleterProvider):
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


class IndicatorAutocompleteProvider(AutocompleterProvider):
    model = Indicator

    provider_name = "ind"

    def get_obj_id(self):
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


class IndicatorAliasedAutocompleteProvider(AutocompleterProvider):
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
            'United States': ['US', 'USA', 'America'],
            'Consumer Price Index': 'CPI',
            'Gross Domestic Product': 'GDP',
            'California': 'CA',
            'Canada': 'CA',
        }


class IndicatorSelectiveAutocompleteProvider(AutocompleterProvider):
    model = Indicator

    provider_name = "indsel"

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

    def include_object(self):
        if self.obj.name == 'US Unemployment Rate':
            return False
        return True

registry.register("stock", StockAutocompleteProvider)
registry.register("mixed", StockAutocompleteProvider)
registry.register("mixed", IndicatorAutocompleteProvider)
registry.register("indicator", IndicatorAutocompleteProvider)
registry.register("indicator_aliased", IndicatorAliasedAutocompleteProvider)
registry.register("indicator_selective", IndicatorSelectiveAutocompleteProvider)