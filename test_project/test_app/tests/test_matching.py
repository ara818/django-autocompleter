#!/usr/bin/python
# -*- coding: utf-8 -*-

from test_app.tests.base import AutocompleterTestCase
from test_app.models import StockAutocompleteProvider, IndicatorAutocompleteProvider
from autocompleter import Autocompleter, registry
from autocompleter import settings as auto_settings


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
        self.assertEqual(len(matches_symbol), 10)

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

    def test_ac_provider_specific_max_results_setting(self):
        """
        Autocompleter/Provider specific MAX_RESULTS is respected
        """
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 10)

        registry.set_ac_provider_setting("stock", StockAutocompleteProvider, 'MAX_RESULTS', 5)
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 5)

        # Must set the setting back to where it was as it will persist
        registry.del_ac_provider_setting("stock", StockAutocompleteProvider, 'MAX_RESULTS')

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


class IndicatorMatchTestCase(AutocompleterTestCase):
    fixtures = ['indicator_test_data_small.json']

    def setUp(self):
        self.autocomp = Autocompleter("indicator")
        self.autocomp.store_all()
        super(IndicatorMatchTestCase, self).setUp()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_same_score_word_based_id_ordering(self):
        """
        Two results with the same score are returned in lexographic order of object ID
        """
        matches = self.autocomp.suggest('us')
        self.assertEqual(matches[1]['display_name'], 'Bank Credit of All US Commercial Banks')
        self.assertEqual(matches[9]['display_name'], 'Trade Weighted US Dollar Index: Major Currencies')
        return matches

    def test_join_char_replacement(self):
        """
        Dashes are handled correctly
        """
        # Testing that both '3-month' and '3 month' match
        matches = self.autocomp.suggest('3-month')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('3 month')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('mortgage-backed')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('mortgagebacked')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('mortgage backed')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('backed mortgage')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('U S A')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('U SA')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('USA')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('U-S-A')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('U/S/A')
        self.assertNotEqual(len(matches), 0)
        matches = self.autocomp.suggest('U-S/A')
        self.assertNotEqual(len(matches), 0)

    def test_min_letters_setting(self):
        """
        MIN_LETTERS is respected.
        """
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 10)
        setattr(auto_settings, 'MIN_LETTERS', 2)
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 0)

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MIN_LETTERS', 1)

    def test_ac_provider_specific_min_letters_setting(self):
        """
        Autocompleter/Provider specific MIN_LETTERS is respected.
        """
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 10)
        setattr(auto_settings, 'MIN_LETTERS', 2)
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 0)

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MIN_LETTERS', 1)


class MultiMatchingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json', 'indicator_test_data_small.json']

    def setUp(self):
        self.autocomp = Autocompleter("mixed")
        self.autocomp.store_all()
        super(MultiMatchingTestCase, self).setUp()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_basic_match(self):
        """
        A single autocompleter can return results from multiple models.
        """
        matches = self.autocomp.suggest('Aapl')
        self.assertEqual(len(matches['stock']), 1)

        matches = self.autocomp.suggest('US Initial Claims')
        self.assertEqual(len(matches['ind']), 1)

        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches['stock']), 10)
        self.assertEqual(len(matches['ind']), 10)

    def test_min_letters_setting(self):
        """
        MIN_LETTERS is respected in multi-type search case.
        """
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches['stock']), 10)
        self.assertEqual(len(matches['ind']), 10)

        setattr(auto_settings, 'MIN_LETTERS', 2)
        matches = self.autocomp.suggest('a')
        self.assertEqual(matches, {})

        setattr(auto_settings, 'MIN_LETTERS', 1)

    def test_ac_provider_specific_min_letters_setting(self):
        """
        Autocompleter/Provider specific MIN_LETTERS is respected in multi-type search case.
        """
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches['stock']), 10)
        self.assertEqual(len(matches['ind']), 10)

        registry.set_ac_provider_setting("mixed", IndicatorAutocompleteProvider, 'MIN_LETTERS', 2)
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 10)
        self.assertEqual('ind' not in matches, True)

        registry.del_ac_provider_setting("mixed", IndicatorAutocompleteProvider, 'MIN_LETTERS')
