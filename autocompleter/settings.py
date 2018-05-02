from django.conf import settings

# Number of seconds to cache results. 0 means no caching
CACHE_TIMEOUT = getattr(settings, 'AUTOCOMPLETER_CACHE_TIMEOUT', 0)

# Regex that filters out characters we ignore for the purposes of autocompleting
CHARACTER_FILTER = getattr(settings, 'AUTOCOMPLETER_CHARACTER_FILTER', r'[^a-z0-9_ ]')

# Whether to redistribute MAX_RESULTS allowance to other result types, on a 
# multi-result type search if possible. 
# Example: If an AC has two results A and B, and MAX_RESULTS = 4, if a given search
# term returns 2 results for A, ELASTIC_RESULTS will allow B to return up to 6 results
ELASTIC_RESULTS = getattr(settings, 'AUTOCOMPLETER_ELASTIC_RESULTS', False)

# When an autocompleter only has one type of result it can return, this setting determines
# whether the results set is "flattened" so that it no longer uses the data structure needed
# to return multi-type results
FLATTEN_SINGLE_TYPE_RESULTS = getattr(settings, 'AUTOCOMPLETER_FLATTEN_SINGLE_TYPE_RESULTS', True)

# Characters we want the autocompleter to interpret as both a space and a blank string.
# Meaning by default, 'U/S-A' will also be stored as 'U SA', 'US A', 'U S A', and 'USA'
JOIN_CHARS = getattr(settings, 'AUTOCOMPLETER_JOIN_CHARS', ['-', '/'])

# Maximum number of results returned per result type
# Note: AC/Provider and Provider override possible
MAX_RESULTS = getattr(settings, 'AUTOCOMPLETER_MAX_RESULTS', 10)

# Maximum number of words in term we should be able to match as exact match. Default is 0,
# which means there is no exact matching at all.
# Note: Provider override possible
MAX_EXACT_MATCH_WORDS = getattr(settings, 'AUTOCOMPLETER_MAX_EXACT_MATCH_WORDS', 0)

# Minimum number of letters required to start returning results
# Note: AC/Provider and Provider override possible
MIN_LETTERS = getattr(settings, 'AUTOCOMPLETER_MIN_LETTERS', 1)

# Whether to detect exact matches and move them to top of the results set (ignoring score)
# This will obviously not work if MAX_EXACT_MATCH_WORDS == 0 for your install or your provider.
# Note: AC/Provider and Provider override possible
MOVE_EXACT_MATCHES_TO_TOP = getattr(settings, 'AUTOCOMPLETER_MOVE_EXACT_MATCHES_TO_TOP', False)

# Redis connection parameters
REDIS_CONNECTION = getattr(settings, 'AUTOCOMPLETER_REDIS_CONNECTION', {})

# Name of variable autcompleter will look for to grab what term to search on.
SUGGEST_PARAMETER_NAME = getattr(settings, 'AUTOCOMPLETER_SUGGEST_PARAMETER_NAME', 'q')

# Test data for debugging/running tests
TEST_DATA = getattr(settings, 'AUTOCOMPLETER_TEST_DATA', False)
