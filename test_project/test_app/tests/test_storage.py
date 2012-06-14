#!/usr/bin/python
# -*- coding: utf-8 -*-

from test_app.tests.base import AutocompleterTestCase
from test_app.models import Stock
from autocompleter import AutocompleterBase, Autocompleter, signal_registry
from autocompleter import settings as auto_settings


class StoringAndRemovingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json', 'indicator_test_data_small.json']

    def test_store_and_remove(self):
        """
        Storing and removing an item works
        """
        autocomp = AutocompleterBase()

        aapl = Stock.objects.get(symbol='AAPL')
        provider = autocomp._get_provider("stock", aapl)

        provider.store()
        keys = self.redis.hkeys('djac.stock')
        self.assertEqual(len(keys), 1)

        provider.remove()
        keys = self.redis.keys('djac.stock*')
        self.assertEqual(len(keys), 0)

    def test_store_and_remove_all_basic(self):
        """
        Storing and removing items all the once works for a single-model autocompleter.
        """
        autocomp = Autocompleter("stock")

        autocomp.store_all()
        keys = self.redis.hkeys('djac.stock')
        self.assertEqual(len(keys), 101)

        autocomp.remove_all()
        keys = self.redis.keys('djac.stock*')
        self.assertEqual(len(keys), 0)

    def test_store_and_remove_all_multi(self):
        """
        Storing and removing items all the once works for a multi-model autocompleter.
        """
        autocomp = Autocompleter("mixed")

        autocomp.store_all()
        keys = self.redis.hkeys('djac.stock')
        self.assertEqual(len(keys), 101)
        keys = self.redis.hkeys('djac.ind')
        self.assertEqual(len(keys), 100)

        autocomp.remove_all()
        keys = self.redis.keys('djac.stock*')
        self.assertEqual(len(keys), 0)
        keys = self.redis.keys('djac.ind*')
        self.assertEqual(len(keys), 0)


class MaxNumWordsStoringTestCase(AutocompleterTestCase):
    fixtures = ['indicator_test_data_small.json']

    def test_max_num_words_setting(self):
        """
        MAX_NUM_WORDS restricts the number matchable phrases stored stored
        """
        autocomp = Autocompleter("indicator")
        autocomp.store_all()
        prefix_keys = self.redis.keys('djac.ind.p*')
        num_keys1 = len(prefix_keys)
        autocomp.remove_all()

        setattr(auto_settings, 'MAX_NUM_WORDS', 3)
        autocomp = Autocompleter("indicator")
        autocomp.store_all()
        prefix_keys = self.redis.keys('djac.ind.p*')
        num_keys2 = len(prefix_keys)
        autocomp.remove_all()

        self.assertTrue(num_keys2 < num_keys1)

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MAX_NUM_WORDS', None)


class SignalBasedStoringTestCase(AutocompleterTestCase):
    def test_listener(self):
        """
        Turning on signals will automatically add and remove and object from the autocompleter
        """
        aapl = Stock(symbol='AAPL', name='Apple', market_cap=50)
        aapl.save()
        keys = self.redis.keys('djac.stock*')
        self.assertEqual(len(keys), 0)

        signal_registry.register(Stock)

        aapl.save()
        keys = self.redis.keys('djac.stock*')
        self.assertNotEqual(len(keys), 0)

        aapl.delete()
        keys = self.redis.keys('djac.stock*')
        self.assertEqual(len(keys), 0)

        signal_registry.unregister(Stock)
