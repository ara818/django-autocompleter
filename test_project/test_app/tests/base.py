import redis

from django_nose import FastFixtureTestCase
from django.conf import settings

class AutocompleterTestCase(FastFixtureTestCase):
    def setUp(self):
        self.redis = redis.Redis(host=settings.AUTOCOMPLETER_REDIS_CONNECTION['host'],
            port=settings.AUTOCOMPLETER_REDIS_CONNECTION['port'],
            db=settings.AUTOCOMPLETER_REDIS_CONNECTION['db']
        )