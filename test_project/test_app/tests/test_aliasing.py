#!/usr/bin/python
# -*- coding: utf-8 -*-

from test_app.tests.base import AutocompleterTestCase
from autocompleter import Autocompleter, registry


class IndicatorAliasedMatchTestCase(AutocompleterTestCase):
    fixtures = ['indicator_test_data_small.json']

    def setUp(self):
        self.autocomp = Autocompleter("indicator_aliased")
        self.autocomp.store_all()
        super(IndicatorAliasedMatchTestCase, self).setUp()

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
        Alias lists do not contain doubles
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
