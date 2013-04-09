#!/usr/bin/python
# -*- coding: utf-8 -*-

from test_app.tests.base import AutocompleterTestCase
from test_app.models import IndicatorAutocompleteProvider
from autocompleter import Autocompleter, registry
from autocompleter import settings as auto_settings


class StockExactStorageTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def test_exact_matches_not_stored_by_default(self):
        """
        Exact matches are not stored by default
        """
        autocomp = Autocompleter("stock")
        autocomp.store_all()
        keys = self.redis.keys('djac.stock.e.*')
        self.assertEqual(len(keys), 0)
        self.assertFalse(self.redis.exists('djac.stock.es'))
        autocomp.remove_all()

    def test_exact_matches_stored_when_turned_on(self):
        """
        We store exact matches when SUPPORT_EXACT_MATCHING is turned on
        """
        setattr(auto_settings, 'SUPPORT_EXACT_MATCHING', True)

        autocomp = Autocompleter("stock")
        autocomp.store_all()
        keys = self.redis.keys('djac.stock.e.*')
        self.assertNotEqual(len(keys), 0)
        self.assertTrue(self.redis.exists('djac.stock.es'))
        autocomp.remove_all()

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'SUPPORT_EXACT_MATCHING', False)


class MultiExactStorageTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json', 'indicator_test_data_small.json']

    def test_exact_matches_not_stored_by_default(self):
        """
        Exact matches are not stored by default, in the multi-provider case
        """
        autocomp = Autocompleter("mixed")
        autocomp.store_all()
        keys = self.redis.keys('djac.stock.e.*')
        self.assertEqual(len(keys), 0)
        self.assertFalse(self.redis.exists('djac.stock.es'))
        keys = self.redis.keys('djac.ind.e.*')
        self.assertEqual(len(keys), 0)
        self.assertFalse(self.redis.exists('djac.ind.es'))
        autocomp.remove_all()

    def test_exact_matches_stored_when_turned_on(self):
        """
        We store exact matches when SUPPORT_EXACT_MATCHING is turned on, in the multi-provider case
        """
        setattr(auto_settings, 'SUPPORT_EXACT_MATCHING', True)

        autocomp = Autocompleter("mixed")
        autocomp.store_all()
        keys = self.redis.keys('djac.stock.e.*')
        self.assertNotEqual(len(keys), 0)
        self.assertTrue(self.redis.exists('djac.stock.es'))
        keys = self.redis.keys('djac.ind.e.*')
        self.assertNotEqual(len(keys), 0)
        self.assertTrue(self.redis.exists('djac.ind.es'))
        autocomp.remove_all()

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'SUPPORT_EXACT_MATCHING', False)

    def test_provider_specific_support_exact_matching_setting(self):
        """
        We can store exact matches for 1 individual provider, and not others
        """
        setattr(auto_settings, 'SUPPORT_EXACT_MATCHING', True)
        registry.set_provider_setting(IndicatorAutocompleteProvider, 'SUPPORT_EXACT_MATCHING', False)

        autocomp = Autocompleter("mixed")
        autocomp.store_all()
        keys = self.redis.keys('djac.stock.e.*')
        self.assertNotEqual(len(keys), 0)
        self.assertFalse(self.redis.exists('djac.stock.es'))
        keys = self.redis.keys('djac.ind.e.*')
        self.assertEqual(len(keys), 0)
        self.assertTrue(self.redis.exists('djac.ind.es'))
        autocomp.remove_all()

        registry.del_provider_setting(IndicatorAutocompleteProvider, 'SUPPORT_EXACT_MATCHING')
        setattr(auto_settings, 'SUPPORT_EXACT_MATCHING', False)


class StockExactMatchTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def setUp(self):
        setattr(auto_settings, 'SUPPORT_EXACT_MATCHING', True)

        self.autocomp = Autocompleter("stock")
        self.autocomp.store_all()
        super(StockExactMatchTestCase, self).setUp()

    def tearDown(self):
        setattr(auto_settings, 'SUPPORT_EXACT_MATCHING', False)
        self.autocomp.remove_all()

    def test_exact_suggest(self):
        """
        Exact matching works
        """
        matches_symbol = self.autocomp.exact_suggest('ma')
        self.assertEqual(len(matches_symbol), 1)

    def test_move_exact_matches_to_top_setting(self):
        """
        MOVE_EXACT_MATCHES_TO_TOP works
        """
        matches = self.autocomp.suggest('Ma')
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', True)
        matches2 = self.autocomp.suggest('Ma')
        self.assertNotEqual(matches[0]['search_name'], matches2[0]['search_name'])

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', False)

    def test_exact_caching(self):
        """
        Exact caching works
        """
        matches = self.autocomp.exact_suggest('aapl')

        setattr(auto_settings, 'CACHE_TIMEOUT', 3600)

        for i in range(0, 10):
            matches2 = self.autocomp.exact_suggest('aapl')

        self.assertEqual(len(matches), len(matches2))

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'CACHE_TIMEOUT', 0)


class MultiExactMatchTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json', 'indicator_test_data_small.json']

    def setUp(self):
        setattr(auto_settings, 'SUPPORT_EXACT_MATCHING', True)

        self.autocomp = Autocompleter("mixed")
        self.autocomp.store_all()
        super(MultiExactMatchTestCase, self).setUp()

    def tearDown(self):
        setattr(auto_settings, 'SUPPORT_EXACT_MATCHING', False)
        self.autocomp.remove_all()

    def test_exact_suggest(self):
        """
        Exact matching works in multi-provider autocompleters
        """
        matches = self.autocomp.exact_suggest('ma')
        self.assertEqual(len(matches['stock']), 1)

        matches = self.autocomp.exact_suggest('US Unemployment Rate')
        self.assertEqual(len(matches['ind']), 1)

    def test_move_exact_matches_to_top(self):
        """
        MOVE_EXACT_MATCHES_TO_TOP works in multi-provider autocompleters
        """
        matches = self.autocomp.suggest('Ma')
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', True)
        matches2 = self.autocomp.suggest('Ma')
        self.assertNotEqual(matches['stock'][0]['search_name'], matches2['stock'][0]['search_name'])
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', False)
