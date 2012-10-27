from django.conf import settings

# Redis connection parameters
REDIS_CONNECTION = getattr(settings, 'AUTOCOMPLETER_REDIS_CONNECTION', {})

# Name of variable autcompleter will look for to grab what term to search on.
SUGGEST_PARAMETER_NAME = getattr(settings, 'AUTOCOMPLETER_SUGGEST_PARAMETER_NAME', 'q')

# Number of seconds to cache results. 0 means no caching
CACHE_TIMEOUT = getattr(settings, 'AUTOCOMPLETER_CACHE_TIMEOUT', 0)

# Regex that filters out characters we ignore for the purposes of autocompleting
CHARACTER_FILTER = getattr(settings, 'AUTOCOMPLETER_CHARACTER_FILTER', r'[^a-z0-9_ ]')

# Maximum number of results returned per result type
# Note: AC/Provider override possible
MAX_RESULTS = getattr(settings, 'AUTOCOMPLETER_MAX_RESULTS', 10)

# Minimum number of letters required to start returning results
# Note: AC/Provider override possible
MIN_LETTERS = getattr(settings, 'AUTOCOMPLETER_MAX_RESULTS', 1)

# Whether to detect exact matches and move them to top of the results set (ignoring score)
MOVE_EXACT_MATCHES_TO_TOP = getattr(settings, 'AUTOCOMPLETER_MOVE_EXACT_MATCHES_TO_TOP', False)

# When an autocompleter only has one type of result it can return, this setting determines
# whether the results set is "flattened" so that it no longer uses the data structure needed
# to return multitype results
FLATTEN_SINGLE_TYPE_RESULTS = getattr(settings, 'AUTOCOMPLETER_FLATTEN_SINGLE_TYPE_RESULTS', True)
