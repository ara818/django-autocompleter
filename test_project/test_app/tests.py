#!/usr/bin/python
# -*- coding: utf-8 -*-

import redis

from django_nose import FastFixtureTestCase
from django.conf import settings

from test_app.models import Stock
from autocompleter import Autocompleter
from autocompleter import settings as auto_settings


class AutocompleterTestCase(FastFixtureTestCase):
    def setUp(self):
        self.redis = redis.Redis(host=settings.AUTOCOMPLETER_REDIS_CONNECTION['host'],
            port=settings.AUTOCOMPLETER_REDIS_CONNECTION['port'],
            db=settings.AUTOCOMPLETER_REDIS_CONNECTION['db']
        )


class StoringAndRemovingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json', 'indicator_test_data_small.json']

    def test_store_and_remove(self):
        """
        Storing and removing an item works
        """
        autocomp = Autocompleter("stock")

        aapl = Stock.objects.get(symbol='AAPL')
        autocomp.store(aapl)
        keys = self.redis.hkeys('djac.stock')
        self.assertEqual(len(keys), 1)

        autocomp.remove(aapl)
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
        """
        A single autocompleter can return results from multiple models.
        """
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

    def test_repeated_matche(self):
        """
        Matching is fast
        """
        setattr(auto_settings, 'MATCH_OUT_OF_ORDER', True)

        for i in range(1, 500):
            self.autocomp.suggest('ma')

        for i in range(1, 500):
            self.autocomp.suggest('price consumer')

        for i in range(1, 500):
            self.autocomp.suggest('a')

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MATCH_OUT_OF_ORDER', False)


class StockMatchTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def setUp(self):
        self.autocomp = Autocompleter("stock")
        self.autocomp.store_all()
        super(StockMatchTestCase, self).setUp()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_simple_match(self):
        """
        Basic matching works
        """
        matches_symbol = self.autocomp.suggest('a')
        self.assertEqual(len(matches_symbol), auto_settings.MAX_RESULTS)

    def test_dual_term_matches(self):
        """
        Items in autocompleter can match against multiple unique terms
        """
        matches_symbol = self.autocomp.suggest('AAPL')
        self.assertEqual(len(matches_symbol), 1)

        matches_name = self.autocomp.suggest('Apple')
        self.assertEqual(len(matches_name), 1)

    def test_accented_matches(self):
        """
        Accented terms match against both their orignal accented form, and their non-accented basic form.
        """
        matches = self.autocomp.suggest('estee lauder')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['search_name'], 'EL')

        matches = self.autocomp.suggest(u'estée lauder')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['search_name'], 'EL')

    def test_exact_matches_setting(self):
        """
        Exact matches are moved to the top
        """
        matches = self.autocomp.suggest('Ma')
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', False)
        matches2 = self.autocomp.suggest('Ma')
        self.assertNotEqual(matches[0]['search_name'], matches2[0]['search_name'])

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', True)

    def test_max_results_setting(self):
        """
        MAX_RESULTS is respected.
        """
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 10)
        setattr(auto_settings, 'MAX_RESULTS', 2)
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 2)

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MAX_RESULTS', 10)


class IndicatorMatchTestCase(AutocompleterTestCase):
    fixtures = ['indicator_test_data_small.json']

    def setUp(self):
        self.autocomp = Autocompleter("indicator")
        self.autocomp.store_all()
        super(IndicatorMatchTestCase, self).setUp()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_out_of_order_matching(self):
        """
        Out of order matching finds results it wouldn't otherwise find
        """
        matches = self.autocomp.suggest('price index consumer')
        self.assertEqual(len(matches), 0)

        setattr(auto_settings, 'MATCH_OUT_OF_ORDER', True)
        matches = self.autocomp.suggest('price index consumer')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('mortgage 30 rate')
        self.assertNotEqual(len(matches), 0)

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MATCH_OUT_OF_ORDER', False)

    def test_out_of_order_duplication(self):
        """
        Out of order matching does not duplicate results
        """
        setattr(auto_settings, 'MATCH_OUT_OF_ORDER', True)

        matches = self.autocomp.suggest('us consumer price index medical')
        self.assertEqual(len(matches), 1)

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

    def test_aliasing(self):
        """
        Various permutations of aliasing work
        """
        matches = self.autocomp.suggest('us consumer price index')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('united states consumer price index')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('us cpi')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('united states consumer price index')
        self.assertNotEqual(len(matches), 0)
