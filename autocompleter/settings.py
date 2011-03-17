from django.conf import settings

REDIS_CONNECTION = getattr(settings, 'AUTOCOMPLETER_REDIS_CONNECTION', {})

MAX_RESULTS = getattr(settings, 'AUTOCOMPLETER_MAX_RESULTS', 10)

MOVE_EXACT_MATCHES_TO_TOP = getattr(settings, 'AUTOCOMPLETER_MOVE_EXACT_MATCHES_TO_TOP', True)
