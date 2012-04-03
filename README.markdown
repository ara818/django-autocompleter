django-completer
================
NOTE: Django autocompleter is undergoing a heavy refactor. stay tuned.

Django completer is redis-backed autocompleter for Django. It provides, fast, seamless autocompletion for Django
models with a minimum of effort.


Short Version
---------------
Consider the model:

    class Stock(models.Model):
        name = models.CharField(max_length=200)
        symbol = models.CharField(max_length=10)
        market_cap = models.DecimalField()

    def __unicode__(self):
        return u'%s' % self.name

