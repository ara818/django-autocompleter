#!/usr/bin/python
# -*- coding: utf-8 -*-

from test_app.tests.base import AutocompleterTestCase
from autocompleter import Autocompleter, registry


class IndicatorAliasedMatchTestCase(AutocompleterTestCase):
    fixtures = ['indicator_test_data_small.json']

    def setUp(self):
        super(IndicatorAliasedMatchTestCase, self).setUp()
        self.autocomp = Autocompleter("indicator_aliased")
        self.autocomp.store_all()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_basic_aliasing(self):
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

        matches = self.autocomp.suggest('u s a consumer price index')
        self.assertNotEqual(len(matches), 0)

    def test_alias_list_creation(self):
        """
        Alias lists have replacement char variations
        """
        provider = registry._providers_by_ac["indicator_aliased"][0]
        aliases = provider.get_norm_phrase_aliases()
        usa_aliases = aliases['usa']
        self.assertTrue('u sa' in usa_aliases)
        self.assertTrue('us a' in usa_aliases)
        self.assertTrue('u s a' in usa_aliases)
        self.assertFalse('usa' in usa_aliases)

    def test_multi_term_aliasing(self):
        matches = self.autocomp.suggest('us consumer price index')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('usa consumer price index')
        self.assertNotEqual(len(matches), 0)

        matches = self.autocomp.suggest('america consumer price index')
        self.assertNotEqual(len(matches), 0)

    def test_double_aliasing(self):
        """
        Double aliasing does not happen.
        California -> CA -> Canada
        """
        matches = self.autocomp.suggest('california unemployment')
        self.assertEqual(len(matches), 1)


class CalcAutocompleteProviderTestCase(AutocompleterTestCase):
    fixtures = ['indicator_test_data_small.json']

    def setUp(self):
        super(CalcAutocompleteProviderTestCase, self).setUp()
        self.autocomp = Autocompleter("metric_aliased")
        self.autocomp.store_all()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_one_way_alias_list_creation(self):
        """
        Test that oneway alias lists are created properly
        """
        provider = registry._providers_by_ac["metric_aliased"][0]
        aliases = provider.get_norm_phrase_aliases()
        self.assertTrue('revenue' in aliases)
        self.assertFalse('turnover' in aliases)

    def test_one_way_aliasing(self):
        """
        Aliases in get_one_way_phrase_aliases are not aliased both ways.
        """
        matches = self.autocomp.suggest('revenue')
        self.assertEqual(len(matches), 1)
        matches = self.autocomp.suggest('Turnover')
        self.assertEqual(len(matches), 2)

    def test_one_way_with_two_way_alias_list_creation(self):
        """
        Two way and one way aliases are both included/treated properly
        """
        provider = registry._providers_by_ac["metric_aliased"][0]
        aliases = provider.get_norm_phrase_aliases()
        self.assertTrue('ev' in aliases)
        self.assertTrue('enterprise value' in aliases)
        self.assertTrue('revenue' in aliases)
        self.assertFalse('turnover' in aliases)

    def test_one_way_with_two_way_aliasing(self):
        """
        Aliases in get_one_way_phrase_aliases are not aliased both ways.
        """
        rev_matches = self.autocomp.suggest('revenue')
        turn_matches = self.autocomp.suggest('Turnover')
        self.assertFalse(rev_matches == turn_matches)

        ev_matches = self.autocomp.suggest('EV')
        ent_val_matches = self.autocomp.suggest('Enterprise Value')
        self.assertEqual(ev_matches, ent_val_matches)
