#!/usr/bin/python
# -*- coding: utf-8 -*-

import redis
import timeit

from django.test import TestCase
from django.conf import settings

from autocompleter_tests.models import Stock
from autocompleter import registry, Autocompleter
from autocompleter import settings as auto_settings

class AutocompleterTestCase(TestCase):
    def setUp(self):
        self.redis = redis.Redis(host=settings.AUTOCOMPLETER_REDIS_CONNECTION['host'], 
            port=settings.AUTOCOMPLETER_REDIS_CONNECTION['port'], 
            db=settings.AUTOCOMPLETER_REDIS_CONNECTION['db']
        )

class StoringAndRemovingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data.json']

    def setUp(self):
        super(StoringAndRemovingTestCase, self).setUp()

    def test_store_and_remove_all(self):
        """
        Store and remove all objects and see if they 
        """
        autocomp = Autocompleter("stock")
        autocomp.store_all()
        keys = self.redis.hkeys(autocomp.auto_base_name)
        self.assertEqual(len(keys), 1000)
        autocomp.remove_all()
        keys = self.redis.hkeys(autocomp.auto_base_name)
        self.assertEqual(len(keys), 0)

class BasicQueryingTestCase(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def setUp(self):
        self.autocomp = Autocompleter("stock")
        self.autocomp.store_all()
        super(BasicQueryingTestCase, self).setUp()
    
    def tearDown(self):
        self.autocomp.remove_all()

    def test_basic_match(self):
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

