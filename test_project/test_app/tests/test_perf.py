#!/usr/bin/python
# -*- coding: utf-8 -*-

from test_app.tests.base import AutocompleterTestCase
from autocompleter import Autocompleter
from autocompleter import settings as auto_settings


class MultiMatchingPerfTestCase(AutocompleterTestCase):
    fixtures = ["stock_test_data.json", "indicator_test_data.json"]
    num_iterations = 1000

    def setUp(self):
        super(MultiMatchingPerfTestCase, self).setUp()
        self.autocomp = Autocompleter("mixed")
        self.autocomp.store_all()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_repeated_matches(self):
        """
        Matching is fast
        """
        setattr(auto_settings, "MATCH_OUT_OF_ORDER_WORDS", True)
        setattr(auto_settings, "MOVE_EXACT_MATCHES_TO_TOP", True)

        for i in range(1, self.num_iterations):
            self.autocomp.suggest("ma")

        for i in range(1, self.num_iterations):
            self.autocomp.suggest("price consumer")

        for i in range(1, self.num_iterations):
            self.autocomp.suggest("a")

        for i in range(1, self.num_iterations):
            self.autocomp.suggest("non revolving")

        # Must set the setting back to where it was as it will persist
        setattr(auto_settings, "MATCH_OUT_OF_ORDER_WORDS", False)
        setattr(auto_settings, "MOVE_EXACT_MATCHES_TO_TOP", True)
