#!/usr/bin/python
# -*- coding: utf-8 -*-

from test_app.tests.base import AutocompleterTestCase
from test_app.autocompleters import IndicatorAutocompleteProvider
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
        keys = self.redis.keys('djac.test.stock.e.*')
        self.assertEqual(len(keys), 0)
        self.assertFalse(self.redis.exists('djac.test.stock.es'))
        autocomp.remove_all()

    def test_exact_matches_stored_when_turned_on(self):
        """
        We store exact matches when MAX_EXACT_MATCH_WORDS is turned on
        """
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 10)

        autocomp = Autocompleter("stock")
        autocomp.store_all()
        keys = self.redis.keys('djac.test.stock.e.*')
        self.assertNotEqual(len(keys), 0)
        self.assertTrue(self.redis.exists('djac.test.stock.es'))
        autocomp.remove_all()

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 0)

    def test_exact_matches_respect_max_words(self):
        """
        We don't store exact matches greater than the number of words in MAX_EXACT_MATCH_WORDS
        """
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 10)
        autocomp = Autocompleter("stock")
        autocomp.store_all()
        matches = autocomp.exact_suggest('International Business Machines Corporation')
        self.assertEqual(len(matches), 1)
        autocomp.remove_all()

        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 2)
        autocomp = Autocompleter("stock")
        autocomp.store_all()
        matches = autocomp.exact_suggest('International Business Machines Corporation')
        self.assertEqual(len(matches), 0)
        autocomp.remove_all()

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 0)


class MultiExactStorageTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json', 'indicator_test_data_small.json']

    def test_exact_matches_not_stored_by_default(self):
        """
        Exact matches are not stored by default, in the multi-provider case
        """
        autocomp = Autocompleter("mixed")
        autocomp.store_all()
        keys = self.redis.keys('djac.test.stock.e.*')
        self.assertEqual(len(keys), 0)
        self.assertFalse(self.redis.exists('djac.test.stock.es'))
        keys = self.redis.keys('djac.test.ind.e.*')
        self.assertEqual(len(keys), 0)
        self.assertFalse(self.redis.exists('djac.test.ind.es'))
        autocomp.remove_all()

    def test_exact_matches_stored_when_turned_on(self):
        """
        We store exact matches when MAX_EXACT_MATCH_WORDS is turned on, in the multi-provider case
        """
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 10)
        autocomp = Autocompleter("mixed")
        autocomp.store_all()
        keys = self.redis.keys('djac.test.stock.e.*')
        self.assertNotEqual(len(keys), 0)
        self.assertTrue(self.redis.exists('djac.test.stock.es'))
        keys = self.redis.keys('djac.test.ind.e.*')
        self.assertNotEqual(len(keys), 0)
        self.assertTrue(self.redis.exists('djac.test.ind.es'))
        autocomp.remove_all()

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 0)

    def test_provider_specific_max_exact_match_words_setting(self):
        """
        We can store exact matches for 1 individual provider, and not others
        """
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 10)
        registry.set_provider_setting(IndicatorAutocompleteProvider, 'MAX_EXACT_MATCH_WORDS', 0)
        autocomp = Autocompleter("mixed")

        autocomp.store_all()
        keys = self.redis.keys('djac.test.stock.e.*')
        self.assertNotEqual(len(keys), 0)
        self.assertTrue(self.redis.exists('djac.test.stock.es'))
        keys = self.redis.keys('djac.test.ind.e.*')
        self.assertEqual(len(keys), 0)
        self.assertFalse(self.redis.exists('djac.test.ind.es'))
        autocomp.remove_all()
        registry.del_provider_setting(IndicatorAutocompleteProvider, 'MAX_EXACT_MATCH_WORDS')

        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 0)


class StockExactMatchTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def setUp(self):
        super(StockExactMatchTestCase, self).setUp()
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 10)

        self.autocomp = Autocompleter("stock")
        self.autocomp.store_all()

    def tearDown(self):
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 0)
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

    def test_move_exact_matches_overridable_at_ac_level(self):
        """
        MOVE_EXACT_MATCHES_TO_TOP can be set at the autocompleter level
        """
        matches = self.autocomp.suggest('Ma')
        registry.set_autocompleter_setting(self.autocomp.name, 'MOVE_EXACT_MATCHES_TO_TOP', True)
        matches2 = self.autocomp.suggest('Ma')
        registry.del_autocompleter_setting(self.autocomp.name, 'MOVE_EXACT_MATCHES_TO_TOP')
        self.assertNotEqual(matches[0]['search_name'], matches2[0]['search_name'])

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
        super(MultiExactMatchTestCase, self).setUp()
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 10)

        self.autocomp = Autocompleter("mixed")
        self.autocomp.store_all()

    def tearDown(self):
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 0)
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

    def test_move_exact_matches_multi_provider_autocompleter_setting(self):
        """
        MOVE_EXACT_MATCHES_TO_TOP works in multi-provider autocompleter at autocompleter level
        """
        matches = self.autocomp.suggest('Ma')
        registry.set_autocompleter_setting(self.autocomp.name, 'MOVE_EXACT_MATCHES_TO_TOP', True)
        matches2 = self.autocomp.suggest('Ma')
        registry.del_autocompleter_setting(self.autocomp.name, 'MOVE_EXACT_MATCHES_TO_TOP')
        self.assertNotEqual(matches['stock'][0]['search_name'], matches2['stock'][0]['search_name'])
