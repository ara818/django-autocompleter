#!/usr/bin/python
# -*- coding: utf-8 -*-

from test_app.tests.base import AutocompleterTestCase
from autocompleter import Autocompleter
from autocompleter import settings as auto_settings


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

    def test_exact_match(self):
        """
        Exact matching works
        """
        matches_symbol = self.autocomp.exact_suggest('ma')
        self.assertEqual(len(matches_symbol), 1)

    def test_no_match(self):
        """
        Phrases that match nothing work
        """
        matches_symbol = self.autocomp.suggest('gobblygook')
        self.assertEqual(len(matches_symbol), 0)

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
        Accented phrases match against both their orignal accented form, and their non-accented basic form.
        """
        matches = self.autocomp.suggest('estee lauder')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['search_name'], 'EL')

        matches = self.autocomp.suggest(u'estée lauder')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['search_name'], 'EL')

    def test_exact_matches_setting(self):
        """
        MOVE_EXACT_MATCHES_TO_TOP works
        """
        matches = self.autocomp.suggest('Ma')
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', True)
        matches2 = self.autocomp.suggest('Ma')
        self.assertNotEqual(matches[0]['search_name'], matches2[0]['search_name'])

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', False)

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

    def test_caching(self):
        """
        Caching works
        """
        matches = self.autocomp.suggest('a')

        setattr(auto_settings, 'CACHE_TIMEOUT', 3600)

        for i in range(0, 3):
            matches2 = self.autocomp.suggest('a')

        self.assertEqual(len(matches), len(matches2))

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'CACHE_TIMEOUT', 0)

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
        MATCH_OUT_OF_ORDER works
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
        MATCH_OUT_OF_ORDER does not cause result duplication
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
        Various permutations of aliased matching work
        """
        matches = self.autocomp.suggest('us consumer price index')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('united states consumer price index')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('us cpi')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('united states consumer price index')
        self.assertNotEqual(len(matches), 0)
