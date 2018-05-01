import json

from .base import AutocompleterTestCase

from django.core.urlresolvers import reverse

from autocompleter import Autocompleter, settings


class TestSuggestView(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def setUp(self):
        super().setUp()
        self.autocomp = Autocompleter('stock')
        self.autocomp.store_all()

    def tearDown(self):
        self.autocomp.remove_all()

    def test_simple_suggest_match(self):
        """
        SuggestView returns 200 status code and correct number of results on match
        """
        suggest_url = reverse('suggest', kwargs={'name': 'stock'})
        matches_symbol = self.autocomp.suggest('a')
        response = self.client.get(suggest_url, data={settings.SUGGEST_PARAMETER_NAME: 'a'})
        self.assertEqual(response.status_code, 200)

        json_response = json.loads(response.content.decode('utf-8'))
        self.assertGreaterEqual(len(json_response), 1)
        self.assertEqual(len(json_response), len(matches_symbol))

    def test_no_suggest_match(self):
        """
        SuggestView returns 200 status code when there is no match
        """
        url = reverse('suggest', kwargs={'name': 'stock'})
        matches_symbol = self.autocomp.suggest('gobblygook')
        response = self.client.get(url, data={settings.SUGGEST_PARAMETER_NAME: 'gobblygook'})
        self.assertEqual(response.status_code, 200)

        json_response = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(json_response), 0)
        self.assertEqual(len(json_response), len(matches_symbol))


class TestExactSuggestView(AutocompleterTestCase):
    fixtures = ['stock_test_data_small.json']

    def setUp(self):
        super().setUp()
        setattr(settings, 'MAX_EXACT_MATCH_WORDS', 10)
        self.autocomp = Autocompleter('stock')
        self.autocomp.store_all()

    def tearDown(self):
        setattr(settings, 'MAX_EXACT_MATCH_WORDS', 0)
        self.autocomp.remove_all()

    def test_simple_exact_suggest_match(self):
        """
        ExactSuggestView returns 200 status code and correct number of results on match
        """
        exact_suggest_url = reverse('exact_suggest', kwargs={'name': 'stock'})
        matches_symbol = self.autocomp.exact_suggest('ma')
        response = self.client.get(exact_suggest_url, data={settings.SUGGEST_PARAMETER_NAME: 'ma'})
        self.assertEqual(response.status_code, 200)

        json_response = json.loads(response.content.decode('utf-8'))
        self.assertGreaterEqual(len(json_response), 1)
        self.assertEqual(len(json_response), len(matches_symbol))

    def test_no_exact_suggest_match(self):
        """
        ExactSuggestView returns 200 status code when there is no match
        """
        url = reverse('exact_suggest', kwargs={'name': 'stock'})
        matches_symbol = self.autocomp.exact_suggest('gobblygook')
        response = self.client.get(url, data={settings.SUGGEST_PARAMETER_NAME: 'gobblygook'})
        self.assertEqual(response.status_code, 200)

        json_response = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(json_response), len(matches_symbol))
