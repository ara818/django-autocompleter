from django.db import models

from autocompleter import registry, AutocompleterProvider, Autocompleter

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    market_cap = models.FloatField(null=True, blank=True)

class StockAutocompleteProvider(AutocompleterProvider):
    model = Stock

    def get_terms(self):
        """
        Term is the name or symbol of the company.
        """
        return [self.obj.name, self.obj.symbol,]

    def get_score(self):
        """
        Score is company inverse of market cap, if available. 
        (High market caps get low scores so they end up first!)
        """
        return 1.0 / self.obj.market_cap

    def get_data(self):
        return {
            'type' : 'stock',
            'id' : self.obj.id,
            'score' : self.get_score(),
            'display_name' : u'%s (%s)' % (self.obj.name, self.obj.symbol),
            'search_name' : self.obj.symbol,
        }

registry.register_named("stock", StockAutocompleteProvider)
registry.register_named("mixed", StockAutocompleteProvider)

class Indicator(models.Model):
    name = models.CharField(max_length=200, unique=True)
    internal_name = models.CharField(max_length=200, unique=True)
    score = models.FloatField(null=True, blank=True)

class IndicatorAutocompleteProvider(AutocompleterProvider):
    model = Indicator

    def get_term(self):
        return self.obj.name

    def get_score(self):
        return self.obj.score

    def get_data(self):
        return {
            'type' : 'indicator',
            'id' : self.obj.id,
            'score' : self.get_score(),
            'display_name' : u'%s' % (self.obj.name,),
            'search_name' : u'%s' % (self.obj.internal_name,),
        }

class IndicatorAliasedAutocompleteProvider(AutocompleterProvider):
    model = Indicator

    def get_term(self):
        return self.obj.name

    def get_score(self):
        return self.obj.score

    def get_data(self):
        return {
            'type' : 'indicator',
            'id' : self.obj.id,
            'score' : self.get_score(),
            'display_name' : u'%s' % (self.obj.name,),
            'search_name' : u'%s' % (self.obj.internal_name,),
        }
    
    @classmethod
    def get_phrase_aliases(self):
        return {
            'US' : 'United States',
            'Consumer Price Index' : 'CPI',
            'Gross Domestic Product' : 'GDP',
        }

registry.register_named("indicator", IndicatorAutocompleteProvider)
registry.register_named("indicator_aliased", IndicatorAliasedAutocompleteProvider)
registry.register_named("mixed", IndicatorAutocompleteProvider)

