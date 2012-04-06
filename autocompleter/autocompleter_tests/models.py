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
