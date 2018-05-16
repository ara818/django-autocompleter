#!/usr/bin/python
# -*- coding: utf-8 -*-

from test_app.tests.base import AutocompleterTestCase
from test_app.autocompleters import StockAutocompleteProvider, IndicatorAutocompleteProvider, CalcAutocompleteProvider
from autocompleter import Autocompleter, registry
from autocompleter import settings as auto_settings


class StockMatchTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def setUp(self):
        super(StockMatchTestCase, self).setUp()
        self.autocomp = Autocompleter("stock")
        self.autocomp.store_all()

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

    def test_dropped_character_matching(self):
        """
        Searching for things that would be normalized to ' ' do not
        result in redis errors.
        """
        matches = self.autocomp.suggest('+')
        self.assertEqual(len(matches), 0)
        matches = self.autocomp.suggest('NBBC vs Regional - Mid-Atlantic Banks vs Financial')
        self.assertEqual(len(matches), 0)


class IndicatorMatchTestCase(AutocompleterTestCase):
    fixtures = ['indicator_test_data_small.json']

    def setUp(self):
        super(IndicatorMatchTestCase, self).setUp()
        self.autocomp = Autocompleter("indicator")
        self.autocomp.store_all()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_same_score_word_based_id_ordering(self):
        """
        Two results with the same score are returned in lexographic order of object ID
        """

        matches = self.autocomp.suggest('us')
        self.assertEqual(matches[1]['display_name'], 'US Dollar to Australian Dollar Exchange Rate')
        self.assertEqual(matches[9]['display_name'], 'US Dollar to Chinese Yuan Exchange Rate')
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


class DictProviderMatchingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def setUp(self):
        super(DictProviderMatchingTestCase, self).setUp()
        self.autocomp = Autocompleter("metric")
        self.autocomp.store_all()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_basic_match(self):
        matches = self.autocomp.suggest('m')
        self.assertEqual(len(matches), 1)


class MultiMatchingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json', 'indicator_test_data_small.json']

    def setUp(self):
        super(MultiMatchingTestCase, self).setUp()
        self.autocomp = Autocompleter("mixed")
        self.autocomp.store_all()

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

        matches = self.autocomp.suggest('m')
        self.assertEqual(len(matches), 3)

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
        registry.set_ac_provider_setting("mixed", CalcAutocompleteProvider, 'MIN_LETTERS', 2)
        matches = self.autocomp.suggest('a')
        self.assertEqual(len(matches), 10)
        self.assertEqual('ind' not in matches, True)

        registry.del_ac_provider_setting("mixed", IndicatorAutocompleteProvider, 'MIN_LETTERS')
        registry.del_ac_provider_setting("mixed", CalcAutocompleteProvider, 'MIN_LETTERS')


class FacetMatchingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def setUp(self):
        super(FacetMatchingTestCase, self).setUp()
        self.autocomp = Autocompleter("faceted_stock")
        self.autocomp.store_all()

    def test_facet_or_match(self):
        """
        Matching using facets works with the 'or' type
        """
        facets = [
            {
                'type': 'or',
                'facets':
                    [
                        {'key': 'sector', 'value': 'Technology'},
                        {'key': 'sector', 'value': 'Consumer Defensive'},
                        {'key': 'sector', 'value': 'Thisdoesntexist'}
                    ]
            }
        ]
        matches = self.autocomp.suggest('a', facets=facets)
        self.assertEqual(len(matches), 4)

    def test_facet_doesnt_skew_suggest(self):
        """
        Test that using facets takes the suggest term into consideration
        """

        matches = self.autocomp.suggest('nosearchresultsforthisterm')
        self.assertEqual(len(matches), 0)
        facets = [
            {
                'type': 'or',
                'facets':
                    [
                        {'key': 'sector', 'value': 'Technology'},
                    ]
            }
        ]

        # we expect that adding facets to a suggest call with no results will not
        # add any results
        facet_matches = self.autocomp.suggest('nosearchresultsforthisterm', facets=facets)
        self.assertEqual(len(facet_matches), 0)

    def test_facet_and_match(self):
        """
        Matching using facets works with the 'and' type
        """
        facets = [
            {
                'type': 'and',
                'facets': [{'key': 'sector', 'value': 'Technology'}, {'key': 'sector', 'value': 'SectorDoesntExist'}]
            }
        ]
        matches = self.autocomp.suggest('ch', facets=facets)
        # since a stock can't have two different values for a sector, we expect calculating an 'and' on
        # two different sectors to have zero matches
        self.assertEqual(len(matches), 0)

        facets = [
            {
                'type': 'and',
                'facets': [
                    {'key': 'sector', 'value': 'Communication Services'},
                    {'key': 'industry', 'value': 'Telecom Services'}
                ]
            }
        ]

        matches = self.autocomp.suggest('ch', facets=facets)
        self.assertEqual(len(matches), 1)

        facets = [
            {
                'type': 'and',
                'facets': [
                    {'key': 'sector', 'value': 'Energy'},
                    {'key': 'industry', 'value': 'Oil & Gas Integrated'}
                ]
            }
        ]
        matches = self.autocomp.suggest('ch', facets=facets)
        self.assertEqual(len(matches), 2)

    def test_facet_match_with_move_exact_matches(self):
        """
        Exact matching still works with facet suggest
        """
        setattr(auto_settings, 'MAX_EXACT_MATCH_WORDS', 10)
        temp_autocomp = Autocompleter('faceted_stock')
        temp_autocomp.store_all()

        facets = [
            {
                'type': 'or',
                'facets': [{'key': 'sector', 'value': 'Technology'}]
            }
        ]

        matches = temp_autocomp.suggest('Ma', facets=facets)
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', True)
        matches2 = temp_autocomp.suggest('Ma', facets=facets)
        self.assertNotEqual(matches[0]['search_name'], matches2[0]['search_name'])

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, 'MOVE_EXACT_MATCHES_TO_TOP', False)
        temp_autocomp.remove_all()

    def test_multiple_facet_dicts_match(self):
        """
        Matching with multiple passed in facet dicts works
        """
        facets = [
            {
                'type': 'and',
                'facets': [{'key': 'sector', 'value': 'Communication Services'}]
            },
            {
                'type': 'and',
                'facets': [{'key': 'industry', 'value': 'Telecom Services'}]
            }
        ]
        matches = self.autocomp.suggest('ch', facets=facets)
        self.assertEqual(len(matches), 1)

        facets = [
            {
                'type': 'and',
                'facets': [{'key': 'sector', 'value': 'Energy'}]
            },
            {
                'type': 'and',
                'facets': [{'key': 'industry', 'value': 'Oil & Gas Integrated'}]
            },
        ]
        matches = self.autocomp.suggest('ch', facets=facets)
        self.assertEqual(len(matches), 2)


class ElasticMatchingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json', 'indicator_test_data_small.json']

    def setUp(self):
        super(ElasticMatchingTestCase, self).setUp()
        self.autocomp = Autocompleter("mixed")
        self.autocomp.store_all()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_basic_match(self):
        """
        Test basic multiple matching works
        """
        matches = self.autocomp.suggest('pe')
        self.assertEqual(len(matches['stock']), 5)
        self.assertEqual(len(matches['ind']), 10)
        self.assertEqual(len(matches['metric']), 1)

    def test_matching_with_max_results_cap(self):
        """
        Test that basic matching with results limit works
        """
        registry.set_ac_provider_setting("mixed", IndicatorAutocompleteProvider, 'MAX_RESULTS', 5)
        registry.set_ac_provider_setting("mixed", StockAutocompleteProvider, 'MAX_RESULTS', 5)
        registry.set_ac_provider_setting("mixed", CalcAutocompleteProvider, 'MAX_RESULTS', 5)

        matches = self.autocomp.suggest('pe')

        self.assertEqual(len(matches['stock']), 5)
        self.assertEqual(len(matches['ind']), 5)
        self.assertEqual(len(matches['metric']), 1)

        registry.del_ac_provider_setting("mixed", IndicatorAutocompleteProvider, 'MAX_RESULTS')
        registry.del_ac_provider_setting("mixed", StockAutocompleteProvider, 'MAX_RESULTS')
        registry.del_ac_provider_setting("mixed", CalcAutocompleteProvider, 'MAX_RESULTS')

    def test_matching_with_max_results_cap_and_elasticity(self):
        """
        Test that simple elastic results
        """
        registry.set_ac_provider_setting("mixed", IndicatorAutocompleteProvider, 'MAX_RESULTS', 5)
        registry.set_ac_provider_setting("mixed", StockAutocompleteProvider, 'MAX_RESULTS', 5)
        registry.set_ac_provider_setting("mixed", CalcAutocompleteProvider, 'MAX_RESULTS', 5)

        setattr(auto_settings, 'ELASTIC_RESULTS', True)

        matches = self.autocomp.suggest('pe')
        self.assertEqual(len(matches['stock']), 5)
        self.assertEqual(len(matches['ind']), 9)
        self.assertEqual(len(matches['metric']), 1)

        setattr(auto_settings, 'ELASTIC_RESULTS', False)
        registry.del_ac_provider_setting("mixed", IndicatorAutocompleteProvider, 'MAX_RESULTS')
        registry.del_ac_provider_setting("mixed", StockAutocompleteProvider, 'MAX_RESULTS')
        registry.del_ac_provider_setting("mixed", CalcAutocompleteProvider, 'MAX_RESULTS')

    def test_matching_with_uneven_max_results_cap_and_elasticity(self):
        """
        Test uneven redistribution of surplus result slots
        """
        registry.set_ac_provider_setting("mixed", IndicatorAutocompleteProvider, 'MAX_RESULTS', 5)
        registry.set_ac_provider_setting("mixed", StockAutocompleteProvider, 'MAX_RESULTS', 4)
        registry.set_ac_provider_setting("mixed", CalcAutocompleteProvider, 'MAX_RESULTS', 6)

        setattr(auto_settings, 'ELASTIC_RESULTS', True)

        matches = self.autocomp.suggest('pe')
        self.assertEqual(len(matches['stock']), 5)
        self.assertEqual(len(matches['ind']), 9)
        self.assertEqual(len(matches['metric']), 1)

        setattr(auto_settings, 'ELASTIC_RESULTS', False)
        registry.del_ac_provider_setting("mixed", IndicatorAutocompleteProvider, 'MAX_RESULTS')
        registry.del_ac_provider_setting("mixed", StockAutocompleteProvider, 'MAX_RESULTS')
        registry.del_ac_provider_setting("mixed", CalcAutocompleteProvider, 'MAX_RESULTS')
