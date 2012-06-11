#!/usr/bin/python
# -*- coding: utf-8 -*-

import redis
import timeit

from django_nose import FastFixtureTestCase
from django.conf import settings

from test_app.models import Stock
from autocompleter import registry, Autocompleter
from autocompleter import settings as auto_settings

class AutocompleterTestCase(FastFixtureTestCase):
    def setUp(self):
        self.redis = redis.Redis(host=settings.AUTOCOMPLETER_REDIS_CONNECTION['host'], 
            port=settings.AUTOCOMPLETER_REDIS_CONNECTION['port'], 
            db=settings.AUTOCOMPLETER_REDIS_CONNECTION['db']
        )

class BasicStoringAndRemovingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def test_store_and_remove_all(self):
        autocomp = Autocompleter("stock")

        aapl = Stock.objects.get(symbol='AAPL')
        autocomp.store(aapl)
        keys = self.redis.hkeys('djac.stock')
        self.assertEqual(len(keys), 1)

        autocomp.remove(aapl)
        keys = self.redis.keys('djac.stock*')
        self.assertEqual(len(keys), 0)

        autocomp.store_all()
        keys = self.redis.hkeys('djac.stock')
        self.assertEqual(len(keys), 101)

        autocomp.remove_all()
        keys = self.redis.keys('djac.stock*')
        self.assertEqual(len(keys), 0)

class MultiStoringAndRemovingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json', 'indicator_test_data_small.json']

    def test_store_and_remove_all(self):
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

class MultiMatchingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json', 'indicator_test_data_small.json']

    def setUp(self):
        self.autocomp = Autocompleter("mixed")
        self.autocomp.store_all()
        super(MultiMatchingTestCase, self).setUp()

    def tearDown(self):
        self.autocomp.remove_all()
        pass

    def test_basic_match(self):
        matches = self.autocomp.suggest('Aapl')
        self.assertEqual(len(matches['stock']), 1)

        matches = self.autocomp.suggest('US Initial Claims')
        self.assertEqual(len(matches['ind']), 1)

        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches['stock']), auto_settings.MAX_RESULTS)
        self.assertEqual(len(matches['ind']), auto_settings.MAX_RESULTS)

class MultiMatchingPerfTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data.json', 'indicator_test_data.json']

    def setUp(self):
        self.autocomp = Autocompleter("mixed")
        self.autocomp.store_all()
        super(MultiMatchingPerfTestCase, self).setUp()

    def tearDown(self):
        self.autocomp.remove_all()
        pass

    def test_short_match(self):
        setattr(auto_settings, 'MATCH_OUT_OF_ORDER', True)

        for i in range(1, 1000):
            matches = self.autocomp.suggest('ma')

        for i in range(1, 1000):
            matches = self.autocomp.suggest('price consumer')

        for i in range(1, 1000):
            matches = self.autocomp.suggest('a')


class StockMatchTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def setUp(self):
        self.autocomp = Autocompleter("stock")
        self.autocomp.store_all()
        super(StockMatchTestCase, self).setUp()
    
    def tearDown(self):
        self.autocomp.remove_all()

    def test_simple_match(self):
        matches_symbol = self.autocomp.suggest('a')
        self.assertTrue(len(matches_symbol) > 0)

    def test_dual_term_matches(self):
        matches_symbol = self.autocomp.suggest('AAPL')
        self.assertEqual(len(matches_symbol), 1)
        
        matches_name = self.autocomp.suggest('Apple')
        self.assertEqual(len(matches_name), 1)

    def test_accented_matches(self):
        matches = self.autocomp.suggest('estee lauder')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['search_name'], 'EL')

        matches = self.autocomp.suggest(u'estée lauder')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['search_name'], 'EL')

    def test_exact_matches_setting(self):
        matches = self.autocomp.suggest('Ma')
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', False)
        matches2 = self.autocomp.suggest('Ma')
        self.assertNotEqual(matches[0]['search_name'], matches2[0]['search_name'])

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', True)

    def test_max_results_setting(self):
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 10)
        setattr(auto_settings, 'MAX_RESULTS', 2)
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 2)

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MAX_RESULTS', 10)

class IndicatorMatchTestCase(AutocompleterTestCase):
    fixtures = ['indicator_test_data.json']

    def setUp(self):
        self.autocomp = Autocompleter("indicator")
        self.autocomp.store_all()
        super(IndicatorMatchTestCase, self).setUp()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_out_of_order_setting(self):
        matches = self.autocomp.suggest('price index consumer')
        self.assertEqual(len(matches), 0)

        setattr(auto_settings, 'MATCH_OUT_OF_ORDER', True)
        matches = self.autocomp.suggest('price index consumer')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('mortgage 30 rate')
        self.assertNotEqual(len(matches), 0)

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MATCH_OUT_OF_ORDER', False)

class IndicatorAliasedMatchTestCase(AutocompleterTestCase):
    fixtures = ['indicator_test_data_small.json']

    def setUp(self):
        self.autocomp = Autocompleter("indicator_aliased")
        self.autocomp.store_all()
        super(IndicatorAliasedMatchTestCase, self).setUp()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_out_of_order_setting(self):
        matches = self.autocomp.suggest('us consumer price index')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('united states consumer price index')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('us cpi')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('united states consumer price index')
        self.assertNotEqual(len(matches), 0)
