import redis

from django.utils.datastructures import SortedDict
import json
from autocompleter import registry, settings, utils

REDIS = redis.Redis(host=settings.REDIS_CONNECTION['host'],
    port=settings.REDIS_CONNECTION['port'],
    db=settings.REDIS_CONNECTION['db'])

AUTO_BASE_NAME = 'djac.%s'
CACHE_BASE_NAME = AUTO_BASE_NAME + '.c.%s'
EXACT_CACHE_BASE_NAME = AUTO_BASE_NAME + '.ce.%s'
PREFIX_BASE_NAME = AUTO_BASE_NAME + '.p.%s'
PREFIX_SET_BASE_NAME = AUTO_BASE_NAME + '.ps'
EXACT_BASE_NAME = AUTO_BASE_NAME + '.e.%s'
EXACT_SET_BASE_NAME = AUTO_BASE_NAME + '.es'


class AutocompleterBase(object):
    def _serialize_data(self, data):
        return json.dumps(data)

    def _deserialize_data(self, raw):
        return json.loads(raw)

    def _get_provider(self, name, obj):
        provider_class = registry.get(name, type(obj))
        if provider_class == None:
            return None
        return provider_class(obj)


class AutocompleterProvider(AutocompleterBase):
    provider_name = None
    _phrase_aliases = None

    def __init__(self, obj):
        self.obj = obj

    def get_obj_id(self):
        """
        The ID for the object, should be unique for each model.
        Will normally not have to override this. However if model is such that
        lots of objects have the same score, autcompleter sorts lexographically by ID
        so it then helps to have this be a unique textual name representing the object instance
        to help make the sorting of the results make sense.
        i.e. for stock it might be company name (assuming unique).
        """
        return str(self.obj.pk)

    def get_term(self):
        """
        The term for the object, which will support autocompletion.
        """
        return str(self.obj)

    def get_terms(self):
        """
        Terms of the objects, which will suport autocompletion.
        Define this if an object can be searched for using more than one term.
        """
        return [self.get_term()]

    def get_norm_terms(self):
        """
        Normalize each term in list of terms. Also, look to see if there are any aliases
        for any words in the term and use them to create alternate normalized terms
        DO NOT override this unless you know what you're doing.
        """
        norm_terms = [utils.get_normalized_term(term) for term in self.get_terms()]
        phrase_aliases = self.__class__.get_norm_phrase_aliases()
        if phrase_aliases == None:
            return norm_terms

        all_norm_terms = []
        for norm_term in norm_terms:
            all_norm_terms = all_norm_terms + utils.get_all_variations(norm_term, phrase_aliases)

        return all_norm_terms

    def get_score(self):
        """
        The score for the object, that will dictate the order of autocompletion.
        """
        return 0

    def get_data(self):
        """
        The data you want to send along on a successful match.
        """
        return {}

    @classmethod
    def get_phrase_aliases(cls):
        """
        If you have aliases (i.e. 'US' = 'United States'), for phrases within
        terms of a particular model, override this function to return a dict of
        key value pairs. Autocompleter will also reverse these aliases.
        So if 'US' maps to 'United States' then 'United States' will map to 'US'
        """
        return {}

    @classmethod
    def get_queryset(cls):
        """
        Get queryset representing all objects represented by this provider.
        Will normally not have to override this.
        """
        return cls.model._default_manager.all()

    @classmethod
    def get_norm_phrase_aliases(cls):
        """
        Take the dict from get_aliases() and normalize / reverse to get ready for
        actual usage.
        DO NOT override this.
        """
        if cls._phrase_aliases == None:
            norm_phrase_aliases = {}

            for key, value in cls.get_phrase_aliases().items():
                norm_key = utils.get_normalized_term(key)
                norm_value = utils.get_normalized_term(value)
                norm_phrase_aliases[norm_key] = norm_value
                norm_phrase_aliases[norm_value] = norm_key
            cls._phrase_aliases = norm_phrase_aliases
        return cls._phrase_aliases

    @classmethod
    def get_provider_name(cls):
        """
        A hook to get the class level provider_name variable when we have an instance.
        DO NOT override this.
        """
        return cls.provider_name

    def store(self):
        """
        Add an object to the autocompleter
        """
        # Init data
        provider_name = self.get_provider_name()
        obj_id = self.get_obj_id()
        norm_terms = self.get_norm_terms()
        score = self.get_score()
        data = self.get_data()

        # Turn each normalized term into possible prefixes
        phrases = []

        for norm_term in norm_terms:
            phrases = phrases + \
                utils.get_autocompleter_phrases_for_term(norm_term, settings.MAX_NUM_WORDS)

        # Start pipeline
        pipe = REDIS.pipeline()

        # Processes prefixes of object, placing object ID in sorted sets
        for phrase in phrases:
            phrase_prefix = ''
            for char in phrase:
                phrase_prefix += char
                # Store prefix to obj ID mapping, with score
                key = PREFIX_BASE_NAME % (provider_name, phrase_prefix,)
                pipe.zadd(key, obj_id, score)

                # Store autocompleter to prefix mapping so we know all prefixes
                # of an autocompleter
                key = PREFIX_SET_BASE_NAME % (provider_name,)
                pipe.sadd(key, phrase_prefix)

        # Process normalized term of object, placing object ID in a sorted set
        # representing exact matches
        for norm_term in norm_terms:
            # Store exact term to obj ID mapping, with score
            key = EXACT_BASE_NAME % (provider_name, norm_term,)
            pipe.zadd(key, obj_id, score)

            # Store autocompleter to exact term mapping so we know all exact terms
            # of an autocompleter
            key = EXACT_SET_BASE_NAME % (provider_name,)
            pipe.sadd(key, norm_term)

        # Store obj ID to data mapping
        key = AUTO_BASE_NAME % (provider_name,)
        pipe.hset(key, obj_id, self._serialize_data(data))

        # End pipeline
        pipe.execute()

    def remove(self):
        """
        Remove an object from the autocompleter
        """
        # Init data
        provider_name = self.get_provider_name()
        obj_id = self.get_obj_id()
        norm_terms = self.get_norm_terms()

        # Turn each normalized term into possible prefixes
        phrases = []
        norm_terms = self.get_norm_terms()
        for norm_term in norm_terms:
            phrases = phrases + \
                utils.get_autocompleter_phrases_for_term(norm_term, settings.MAX_NUM_WORDS)

        # Start pipeline
        pipe = REDIS.pipeline()

        # Processes prefixes of object, removing object ID from sorted sets
        for phrase in phrases:
            phrase_prefix = ''
            for char in phrase:
                phrase_prefix += char
                key = PREFIX_BASE_NAME % (provider_name, phrase_prefix,)
                pipe.zrem(key, obj_id)

                key = PREFIX_SET_BASE_NAME % (provider_name,)
                pipe.srem(key, phrase_prefix)

        # Process normalized terms of object, removing object ID from a sorted set
        # representing exact matches
        for norm_term in norm_terms:
            key = EXACT_BASE_NAME % (provider_name, norm_term,)
            pipe.zrem(key, obj_id)

            key = EXACT_SET_BASE_NAME % (provider_name,)
            pipe.srem(key, norm_term)

        # Remove model ID to data mapping
        key = AUTO_BASE_NAME % (provider_name,)
        pipe.hdel(key, obj_id)

        # End pipeline
        pipe.execute()


class Autocompleter(AutocompleterBase):
    """
    Autocompleter class
    """
    def __init__(self, name=settings.DEFAULT_NAME):
        self.name = name

    def store_all(self):
        """
        Store all objects of all providers register with this autocompleter.
        """
        provider_classes = self._get_all_providers_by_autocompleter()
        if provider_classes == None:
            return

        for provider_class in provider_classes:
            for obj in provider_class.get_queryset().iterator():
                provider_class(obj).store()

    def remove_all(self):
        """
        Remove all objects for a given autocompleter.
        This will clear the autocompleter even when the underlying objects don't exist.
        """
        provider_classes = self._get_all_providers_by_autocompleter()
        if provider_classes == None:
            return

        for provider_class in provider_classes:
            provider_name = provider_class.provider_name

            # Get list of all prefixes for autocompleter
            prefix_set_name = PREFIX_SET_BASE_NAME % (provider_name,)
            prefixes = REDIS.smembers(prefix_set_name)

            # Get list of all exact match terms for autocompleter
            exact_set_name = EXACT_SET_BASE_NAME % (provider_name,)
            norm_terms = REDIS.smembers(exact_set_name)

            # Start pipeline
            pipe = REDIS.pipeline()

            # For each prefix, delete sorted set
            for prefix in prefixes:
                key = PREFIX_BASE_NAME % (provider_name, prefix,)
                pipe.delete(key)
            # Delete the set of prefixes
            pipe.delete(prefix_set_name)

            # For each exact match term, deleting sorted set
            for norm_term in norm_terms:
                key = EXACT_BASE_NAME % (provider_name, norm_term,)
                pipe.delete(key)
            # Delete the set of exact matches
            pipe.delete(exact_set_name)

            # Remove the entire obj ID to data mapping hash
            key = AUTO_BASE_NAME % (provider_name,)
            pipe.delete(key)

            # End pipeline
            pipe.execute()

        # Just to be extra super clean, let's delete all cached results
        # for this autocompleter
        cache_key = CACHE_BASE_NAME % (self.name, '*',)
        exact_cache_key = EXACT_CACHE_BASE_NAME % (self.name, '*',)

        keys = REDIS.keys(cache_key) + REDIS.keys(exact_cache_key)
        if len(keys) > 0:
            REDIS.delete(*keys)

    def suggest(self, term):
        """
        Suggest matching objects, given a term
        """
        providers = self._get_all_providers_by_autocompleter()
        if providers == None:
            return []

        norm_term = utils.get_normalized_term(term)
        cache_key = CACHE_BASE_NAME % (self.name, norm_term,)

        # If we have a cached version of the search results available, return it!
        if settings.CACHE_TIMEOUT and REDIS.exists(cache_key):
            return self._deserialize_data(REDIS.get(cache_key))

        num_providers = len(providers)
        provider_results = SortedDict()
        norm_words = norm_term.split()
        num_words = len(norm_words)

        # Get the matched result IDs
        pipe = REDIS.pipeline()
        for provider in providers:
            provider_name = provider.provider_name

            # Get base autocompleter matches
            key = PREFIX_BASE_NAME % (provider_name, norm_term,)
            pipe.zrevrange(key, 0, settings.MAX_RESULTS - 1)

            # Get exact matches
            if settings.MOVE_EXACT_MATCHES_TO_TOP:
                key = EXACT_BASE_NAME % (provider_name, norm_term,)
                pipe.zrevrange(key, 0, settings.MAX_RESULTS - 1)

            # Get out of order matches
            if settings.MATCH_OUT_OF_ORDER and num_words > 1:
                keys = [PREFIX_BASE_NAME % (provider_name, i,) for i in norm_words]
                pipe.zinterstore("oooresults", keys, aggregate='MIN')
                pipe.zrevrange("oooresults", 0, settings.MAX_RESULTS - 1)
        results = [i for i in pipe.execute() if type(i) == list]

        # Create a dict mapping provider to result IDs
        # We combine the 3 different kinds of results into 1 result ID list per provider.
        for i in range(0, num_providers):
            provider_name = providers[i].provider_name
            ids = results.pop(0)

            # We merge exact matches with base matches by moving them to
            # the head of the results
            if settings.MOVE_EXACT_MATCHES_TO_TOP:
                exact_ids = results.pop(0)

                # Need to reverse exact IDs so high scores are behind low scores, since we
                # are inserted in front of list.
                exact_ids.reverse()

                # Merge exact IDs with non-exact IDs, puttting exacts IDs in front and removing
                # from regular ID list if necessary
                for j in exact_ids:
                    if j in ids:
                        ids.remove(j)
                    ids.insert(0, j)

            # Add in out of order matches to the end of the list, where they don't already exist
            if settings.MATCH_OUT_OF_ORDER and num_words > 1:
                for j in results.pop(0):
                    if j not in ids:
                        ids.append(j)

            provider_results[provider_name] = ids[:settings.MAX_RESULTS]

        results = self._get_results_from_ids(provider_results)

        # If told to, cache the final results for CACHE_TIMEOUT secnds
        if settings.CACHE_TIMEOUT:
            REDIS.set(cache_key, self._serialize_data(results))
            REDIS.expire(cache_key, settings.CACHE_TIMEOUT)

        return results

    def exact_suggest(self, term):
        """
        Suggest matching objects exacting matching term given, given a term
        """
        providers = self._get_all_providers_by_autocompleter()
        if providers == None:
            return []

        norm_term = utils.get_normalized_term(term)
        cache_key = EXACT_CACHE_BASE_NAME % (self.name, norm_term,)

        # If we have a cached version of the search results available, return it!
        if settings.CACHE_TIMEOUT and REDIS.exists(cache_key):
            return self._deserialize_data(REDIS.get(cache_key))

        num_providers = len(providers)
        provider_results = SortedDict()

        # Get the matched result IDs
        pipe = REDIS.pipeline()
        for provider in providers:
            provider_name = provider.provider_name
            key = EXACT_BASE_NAME % (provider_name, norm_term,)
            pipe.zrevrange(key, 0, settings.MAX_RESULTS - 1)
        results = pipe.execute()

        # Create a dict mapping provider to result IDs
        for i in range(0, num_providers):
            provider_name = providers[i].provider_name
            exact_ids = results.pop(0)
            provider_results[provider_name] = exact_ids[:settings.MAX_RESULTS]

        results = self._get_results_from_ids(provider_results)

        # If told to, cache the final results for CACHE_TIMEOUT secnds
        if settings.CACHE_TIMEOUT:
            REDIS.set(cache_key, self._serialize_data(results))
            REDIS.expire(cache_key, settings.CACHE_TIMEOUT)
        return results

    def _get_results_from_ids(self, provider_results):
        """
        Given a dict mapping providers to results IDs, return
        a dict mapping providers to results
        """
        num_providers = len(provider_results.keys())
        # Get the results for each provider
        pipe = REDIS.pipeline()
        for provider_name, ids in provider_results.items():
            if len(ids) > 0:
                key = AUTO_BASE_NAME % (provider_name,)
                pipe.hmget(key, ids)
        results = pipe.execute()

        # Put them in the  provider results didct
        for provider_name, ids in provider_results.items():
            if len(ids) > 0:
                provider_results[provider_name] = \
                    [self._deserialize_data(i) for i in results.pop(0) if i != None]

        # If we only have one type of provider, don't bother sending the provider dict,
        # just the results list is sufficient
        if num_providers == 1:
            return provider_results.values()[0]
        return provider_results

    def _get_all_providers_by_autocompleter(self):
        return registry.get_all_by_autocompleter(self.name)
