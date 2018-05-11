from collections import OrderedDict
import redis
import json
import itertools
import uuid

from autocompleter import registry, settings, utils

REDIS = redis.Redis(host=settings.REDIS_CONNECTION['host'],
    port=settings.REDIS_CONNECTION['port'],
    db=settings.REDIS_CONNECTION['db'])

if settings.TEST_DATA:
    AUTO_BASE_NAME = 'djac.test.%s'
else:
    AUTO_BASE_NAME = 'djac.%s'
CACHE_BASE_NAME = AUTO_BASE_NAME + '.c.%s'
EXACT_CACHE_BASE_NAME = AUTO_BASE_NAME + '.ce.%s'
PREFIX_BASE_NAME = AUTO_BASE_NAME + '.p.%s'
PREFIX_SET_BASE_NAME = AUTO_BASE_NAME + '.ps'
EXACT_BASE_NAME = AUTO_BASE_NAME + '.e.%s'
EXACT_SET_BASE_NAME = AUTO_BASE_NAME + '.es'
TERM_SET_BASE_NAME = AUTO_BASE_NAME + '.ts'
RESULT_SET_BASE_NAME = 'djac.results.%s'
FACET_SET_BASE_NAME = AUTO_BASE_NAME + '.f.%s'
FACET_MAP_BASE_NAME = AUTO_BASE_NAME + '.fm'


class AutocompleterBase(object):
    @classmethod
    def _serialize_data(cls, data):
        return json.dumps(data)

    @classmethod
    def _deserialize_data(cls, raw):
        return json.loads(raw.decode('utf-8'))


class AutocompleterProviderBase(AutocompleterBase):
    # Name in redis that data for this provider will be stored. To preserve memory, keep this short.
    provider_name = None
    # Cache of all aliases for this provider, including all possible variations
    _phrase_aliases = None

    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        return self.provider_name

    def get_score(self):
        """
        The score for the object, that will dictate the order of autocompletion.
        """
        return 0

    def _get_score(self):
        # Redis orders low to high, with equal scores being sorted lexographically by obj ID,
        # so here we convert high to low score to low to high. Note that we can not use
        # ZREVRANGE instead because that sorts obj IDs lexograpahically ascending. Using
        # low to high scores allows for people to have autocompleters with lots of objects
        # with the same score and a word based object ID (say, a unique name) and have these
        # objects returned in alphabetical order when they have the same score.try:
        score = self.get_score()
        try:
            score = 1 / float(score)
        except ZeroDivisionError:
            score = float('inf')
        return score

    def get_terms(self):
        """
        Terms of the objects, which will support autocompletion.
        Define this if an object can be searched for using more than one term.
        """
        return [self.get_term()]

    @classmethod
    def _get_norm_terms(cls, terms):
        """
        Normalize each term in list of terms. Also, look to see if there are any aliases
        for any words in the term and use them to create alternate normalized terms
        DO NOT override this
        """
        norm_terms = [utils.get_norm_term_variations(term) for term in terms]
        norm_terms = itertools.chain(*norm_terms)

        norm_terms_with_variations = []
        # Now we get alternate norm terms by looking for alias phrases in any of the terms
        phrase_aliases = cls.get_norm_phrase_aliases()
        if phrase_aliases is not None:
            for norm_term in norm_terms:
                norm_terms_with_variations = norm_terms_with_variations + \
                    utils.get_aliased_variations(norm_term, phrase_aliases)

        return norm_terms_with_variations

    @classmethod
    def get_phrase_aliases(cls):
        """
        If you have aliases (i.e. 'US' = 'United States'), for phrases within
        terms of a particular model, override this function to return a dict of
        key value pairs. Autocompleter will also reverse these aliases.
        So if 'US' maps to 'United States' then 'United States' will map to 'US'

        {x: y} means to the AC that x is also y, and y is also x
        """
        return {}

    @classmethod
    def get_one_way_phrase_aliases(cls):
        """
        If you have aliases (i.e. 'US' = 'United States'), for phrases within
        terms of a particular model, override this function to return a dict of
        key value pairs. Autocompleter will NOT reverse these.

        {x: y} means to the AC that x is also y, but y is not x
        """
        return {}

    @classmethod
    def get_norm_phrase_aliases(cls):
        """
        Take the dict from get_aliases() and normalize / reverse to get ready for
        actual usage.
        DO NOT override this.
        """
        if cls._phrase_aliases is not None:
            return cls._phrase_aliases

        norm_phrase_aliases = utils.build_norm_phrase_alias_dict(cls.get_phrase_aliases())
        one_way_phrase_aliases = cls.get_one_way_phrase_aliases()
        one_way_norm_phrase_aliases = utils.build_norm_phrase_alias_dict(one_way_phrase_aliases, two_way=False)

        norm_phrase_aliases.update(one_way_norm_phrase_aliases)
        cls._phrase_aliases = norm_phrase_aliases
        return cls._phrase_aliases

    @classmethod
    def get_provider_name(cls):
        """
        A hook to get the class level provider_name variable when we have an instance.
        DO NOT override this.
        """
        return cls.provider_name

    @classmethod
    def delete_old_terms(cls, obj_id, old_terms):
        """
        Gets rid of old terms based on terms listed in the id-terms mapping.
        """
        old_norm_terms = cls._get_norm_terms(old_terms)
        cls.clear_keys(obj_id, old_norm_terms)

    @classmethod
    def get_old_terms(cls, obj_id):
        key = TERM_SET_BASE_NAME % (cls.get_provider_name(),)
        old_terms = REDIS.hget(key, obj_id)
        if old_terms is not None:
            old_terms = cls._deserialize_data(old_terms)
        return old_terms

    @classmethod
    def delete_old_facets(cls, obj_id, old_facets):
        provider_name = cls.get_provider_name()
        pipe = REDIS.pipeline()
        # Remove old facets from the corresponding facet sorted set.
        for facet in old_facets:
            try:
                facet_value = facet['value']
                facet_set_name = FACET_SET_BASE_NAME % (provider_name, facet_value,)
                pipe.zrem(facet_set_name, obj_id)
            except KeyError:
                continue
        # Now delete the mapping from this obj_id -> facet values
        facet_map_name = FACET_MAP_BASE_NAME % (provider_name,)
        pipe.hdel(facet_map_name, obj_id)

        # End pipeline
        pipe.execute()

    @classmethod
    def get_old_facets(cls, obj_id):
        facet_map_name = FACET_MAP_BASE_NAME % (cls.get_provider_name(),)
        old_facets = REDIS.hget(facet_map_name, obj_id)
        if old_facets is not None:
            old_facets = cls._deserialize_data(old_facets)
        return old_facets

    @classmethod
    def clear_keys(cls, obj_id, norm_terms):
        provider_name = cls.get_provider_name()
        # Start pipeline
        pipe = REDIS.pipeline()
        # Processes prefixes of object, removing object ID from sorted sets
        for norm_term in norm_terms:
            norm_words = norm_term.split(' ')
            for norm_word in norm_words:
                word_prefix = ''
                for char in norm_word:
                    word_prefix += char
                    key = PREFIX_BASE_NAME % (provider_name, word_prefix,)
                    pipe.zrem(key, obj_id)

                    key = PREFIX_SET_BASE_NAME % (provider_name,)
                    pipe.srem(key, word_prefix)

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

        # Remove obj_id to terms mapping
        key = TERM_SET_BASE_NAME % (provider_name,)
        pipe.hdel(key, obj_id)

        # End pipeline
        pipe.execute()

    @classmethod
    def get_facets(cls):
        """
        """
        return []

    def get_data(self):
        """
        The data you want to send along on a successful match.
        """
        return {}

    def include_item(self):
        """
        Whether this object should be included in the autocompleter at all. By default, all objects
        in the model are included.
        """
        return True

    def store(self, delete_old=True):
        """
        Add an object to the autocompleter
        DO NOT override this.
        """
        # Init data
        if not self.include_item():
            return
        provider_name = self.get_provider_name()
        obj_id = self.get_item_id()
        terms = self.get_terms()
        norm_terms = self.__class__._get_norm_terms(terms)
        score = self._get_score()
        data = self.get_data()
        facets = self.get_facets()

        old_terms = self.__class__.get_old_terms(obj_id)
        old_facets = self.__class__.get_old_facets(obj_id)

        updated_terms = terms != old_terms
        updated_facets = facets != old_facets

        # Check if the terms or facets have been updated. If both weren't updated,
        # then we can just update the data payload and short circuit.
        if not updated_terms and not updated_facets:
            # Store obj ID to data mapping
            key = AUTO_BASE_NAME % (provider_name,)
            REDIS.hset(key, obj_id, self.__class__._serialize_data(data))
            return

        # Clear out the obj_id's old data if told to
        if delete_old is True:
            # TODO: memoize get_old_terms? Otherwise have to pass old_terms down the line to avoid
            # doing 2 extra redis queries.
            if updated_terms and old_terms is not None:
                self.__class__.delete_old_terms(obj_id, old_terms)
            if updated_facets and old_facets is not None:
                self.__class__.delete_old_facets(obj_id, old_facets)

        # Start pipeline
        pipe = REDIS.pipeline()

        # Processes prefixes of object, placing object ID in sorted sets
        for norm_term in norm_terms:
            norm_words = norm_term.split(' ')
            for norm_word in norm_words:
                word_prefix = ''
                for char in norm_word:
                    word_prefix += char
                    # Store prefix to obj ID mapping, with score
                    key = PREFIX_BASE_NAME % (provider_name, word_prefix,)
                    pipe.zadd(key, obj_id, score)
                    # Store autocompleter to prefix mapping so we know all prefixes
                    # of an autocompleter
                    key = PREFIX_SET_BASE_NAME % (provider_name,)
                    pipe.sadd(key, word_prefix)

        # Process normalized term of object, placing object ID in a sorted set
        # representing exact matches
        max_exact_match_words = registry.get_provider_setting(self, 'MAX_EXACT_MATCH_WORDS')
        if max_exact_match_words > 0:
            for norm_term in norm_terms:
                if len(norm_term.split(' ')) > max_exact_match_words:
                    continue
                # Store exact term to obj ID mapping, with score
                key = EXACT_BASE_NAME % (provider_name, norm_term,)
                pipe.zadd(key, obj_id, score)

                # Store autocompleter to exact term mapping so we know all exact terms
                # of an autocompleter
                key = EXACT_SET_BASE_NAME % (provider_name,)
                pipe.sadd(key, norm_term)

        facets_added = []
        for facet in facets:
            try:
                facet_key = facet['key']
                expected_facet_value = facet['value']
                actual_facet_value = data[facet_key]
                if actual_facet_value == expected_facet_value:
                    facet_set_name = FACET_SET_BASE_NAME % (provider_name, actual_facet_value,)
                    pipe.zadd(facet_set_name, obj_id, score)
                    facets_added.append(facet)
            except KeyError:
                continue

        # Store obj ID to data mapping
        key = AUTO_BASE_NAME % (provider_name,)
        pipe.hset(key, obj_id, self.__class__._serialize_data(data))

        # set provider's obj_id - terms hash.
        key = TERM_SET_BASE_NAME % (provider_name,)
        serialized_terms = self.__class__._serialize_data(terms)
        pipe.hset(key, obj_id, serialized_terms)

        # Map provider's obj_id -> facet values
        if len(facets_added) > 0:
            facet_map_name = FACET_MAP_BASE_NAME % (provider_name,)
            pipe.hset(facet_map_name, obj_id, self.__class__._serialize_data(facets_added))

        # End pipeline
        pipe.execute()

    def remove(self):
        """
        Remove an object from the autocompleter
        DO NOT override this.
        """
        # Init data
        obj_id = self.get_item_id()
        terms = self.__class__.get_old_terms(obj_id)
        if terms is not None:
            self.__class__.delete_old_terms(obj_id, terms)
        facets = self.__class__.get_old_facets(obj_id)
        if facets is not None:
            self.__class__.delete_old_facets(obj_id, facets)


class AutocompleterModelProvider(AutocompleterProviderBase):
    # Model this provider is related to
    model = None

    def get_item_id(self):
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

    @classmethod
    def get_iterator(cls):
        """
        Get queryset representing all objects represented by this provider.
        Will normally not have to override this.
        """
        return cls.model._default_manager.iterator()


class AutocompleterDictProvider(AutocompleterProviderBase):
    # Model this provider is related to
    obj_dict = None

    def get_item_id(self):
        """
        Select a field which is unique for use in the autocompleter.
        Unlike the model provider, there is no sensible default so this MUST be overridden
        """
        raise NotImplementedError

    def get_term(self):
        """
        The term for the item, which will support autocompletion.
        Unlike the model provider, there is no sensible default so this MUST be overridden
        """
        raise NotImplementedError

    @classmethod
    def get_iterator(cls):
        """
        For the dict provider, the items specified on the attr should be good to go,
        but it can be overridden here.
        """
        return cls.obj_dict


class Autocompleter(AutocompleterBase):
    """
    Autocompleter class
    """
    def __init__(self, name):
        self.name = name

    def store_all(self, delete_old=True):
        """
        Store all objects of all providers register with this autocompleter.
        """
        provider_classes = self._get_all_providers_by_autocompleter()
        if provider_classes is None:
            return

        for provider_class in provider_classes:
            for obj in provider_class.get_iterator():
                provider_class(obj).store(delete_old=delete_old)

    def remove_all(self):
        """
        Remove all objects for a given autocompleter.
        This will clear the autocompleter even when the underlying objects don't exist.
        """
        provider_classes = self._get_all_providers_by_autocompleter()
        if provider_classes is None:
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

            # There is a possibility that some straggling keys have not been
            # cleaned up if their ID changed but for some reason we did not
            # delete the old ID... Here we delete what's left, just to be safe
            key = AUTO_BASE_NAME % (provider_name,)
            key += '*'
            leftovers = REDIS.keys(key)

            # Start pipeline
            pipe = REDIS.pipeline()

            for i in leftovers:
                pipe.delete(i)

            # End pipeline
            pipe.execute()

        # Just to be extra super clean, let's delete all cached results
        # for this autocompleter
        self.clear_cache()

    def clear_cache(self):
        """
        Clear cache
        """
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
        if providers is None:
            return []

        # If we have a cached version of the search results available, return it!
        cache_key = CACHE_BASE_NAME % \
            (self.name, utils.get_normalized_term(term, settings.JOIN_CHARS))
        if settings.CACHE_TIMEOUT and REDIS.exists(cache_key):
            return self.__class__._deserialize_data(REDIS.get(cache_key))

        # Get the normalized term variations we need to search for each term. A single term
        # could turn into multiple terms we need to search.
        norm_terms = utils.get_norm_term_variations(term)
        if len(norm_terms) == 0:
            return []

        provider_results = OrderedDict()

        # Get the matched result IDs
        total_results = 0
        if settings.ELASTIC_RESULTS:
            for provider in providers:
                total_results += registry.get_ac_provider_setting(self.name, provider, 'MAX_RESULTS')

        # Generate a unique identifier to be used for storing intermediate results. This is to
        # prevent redis key collisions between competing suggest / exact_suggest calls.
        uuid_str = str(uuid.uuid4())
        intermediate_result_key = RESULT_SET_BASE_NAME % (uuid_str,)

        pipe = REDIS.pipeline()
        for provider in providers:
            provider_name = provider.provider_name
            # If we have total_results from adding up all MAX_RESULTS from ELASTIC_RESULTS use it.
            if settings.ELASTIC_RESULTS:
                MAX_RESULTS = total_results
            else:
                MAX_RESULTS = registry.get_ac_provider_setting(self.name, provider, 'MAX_RESULTS')
            # If the total length of the term is less than MIN_LETTERS allowed, then don't search
            # the provider for this term
            MIN_LETTERS = registry.get_ac_provider_setting(self.name, provider, 'MIN_LETTERS')
            if len(term) < MIN_LETTERS:
                continue

            result_keys = []
            for norm_term in norm_terms:
                norm_words = norm_term.split()
                term_result_key = intermediate_result_key + '.' + norm_term
                result_keys.append(term_result_key)
                keys = [PREFIX_BASE_NAME % (provider_name, norm_word,) for norm_word in norm_words]
                pipe.zinterstore(term_result_key, keys, aggregate='MIN')
            pipe.zunionstore(intermediate_result_key, result_keys, aggregate='MIN')
            for term_result_key in result_keys:
                pipe.delete(term_result_key)
            pipe.zrange(intermediate_result_key, 0, MAX_RESULTS - 1)

            # Get exact matches
            if settings.MOVE_EXACT_MATCHES_TO_TOP:
                keys = []
                for norm_term in norm_terms:
                    keys.append(EXACT_BASE_NAME % (provider_name, norm_term,))
                # Do not attempt zunionstore on empty list because redis errors out.
                if len(keys) == 0:
                    continue

                pipe.zunionstore(intermediate_result_key, keys, aggregate='MIN')
                pipe.zrange(intermediate_result_key, 0, MAX_RESULTS - 1)
            pipe.delete(intermediate_result_key)

        results = [i for i in pipe.execute() if type(i) == list]

        # init mappings and surplus for Elastic Result distribution
        deficits = {}
        # Mapping required to store result_ids outside of per provider loop before
        # fetching items / redistributing availabe result slots in elastic results
        provider_result_ids = {}
        max_results_dict = {}
        # total pool of available result slots
        total_surplus = 0
        # Create a dict mapping provider to result IDs
        # We combine the 2 different kinds of results into 1 result ID list per provider.
        for provider in providers:
            provider_name = provider.provider_name

            MAX_RESULTS = registry.get_ac_provider_setting(self.name, provider, 'MAX_RESULTS')
            # If the total length of the term is less than MIN_LETTERS allowed, then don't search
            # the provider for this term
            MIN_LETTERS = registry.get_ac_provider_setting(self.name, provider, 'MIN_LETTERS')
            if len(term) < MIN_LETTERS:
                # if provider will not be used due to min_letters, put all result slots
                # in surplus pool then continue
                total_surplus += MAX_RESULTS
                continue

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
            provider_result_ids[provider] = ids

            if settings.ELASTIC_RESULTS:
                surplus = MAX_RESULTS - len(ids)
                if surplus >= 0:
                    max_results_dict[provider] = len(ids)
                    total_surplus += surplus
                else:
                    # create base usage
                    max_results_dict[provider] = MAX_RESULTS
                    # create dict of how many extra each provider actually needs
                    deficits[provider] = surplus * -1
            else:
                max_results_dict[provider] = MAX_RESULTS

        if settings.ELASTIC_RESULTS:
            while total_surplus > 0:
                # get a list of providers with deficits for two reasons. First, to know how
                # to divide the surplus, secondly, to iterate over rather than the deficit dict
                # as we will be manipulating the dict in the for loop
                beneficiaries = list(deficits.keys())
                num_beneficiaries = len(beneficiaries)
                # if num_beneficiaries is greater than surplus, surplus_each will be 0 because of int
                # division in python, but total_surplus will still be > 0, resulting in infinite loop.
                if num_beneficiaries == 0 or num_beneficiaries > total_surplus:
                    break
                else:
                    surplus_payout = int(total_surplus / num_beneficiaries)
                    for provider in beneficiaries:
                        deficit = deficits.pop(provider)
                        if (deficit - surplus_payout) <= 0:
                            total_surplus -= deficit
                            max_results_dict[provider] += surplus_payout
                        else:
                            total_surplus -= surplus_payout
                            max_results_dict[provider] += surplus_payout
                            deficits[provider] = deficit - surplus_payout

        for provider in providers:
            try:
                max_results = max_results_dict[provider]
                provider_results[provider.provider_name] = provider_result_ids[provider][:max_results]
            except KeyError:
                continue

        results = self._get_results_from_ids(provider_results)

        # If told to, cache the final results for CACHE_TIMEOUT secnds
        if settings.CACHE_TIMEOUT:
            REDIS.setex(cache_key, self.__class__._serialize_data(results), settings.CACHE_TIMEOUT)
        return results

    def exact_suggest(self, term):
        """
        Suggest matching objects exacting matching term given, given a term
        """
        providers = self._get_all_providers_by_autocompleter()
        if providers is None:
            return []

        # If we have a cached version of the search results available, return it!
        cache_key = EXACT_CACHE_BASE_NAME % (self.name, term,)
        if settings.CACHE_TIMEOUT and REDIS.exists(cache_key):
            return self.__class__._deserialize_data(REDIS.get(cache_key))
        provider_results = OrderedDict()

        # Get the normalized we need to search for each term... A single term
        # could turn into multiple terms we need to search.
        norm_terms = utils.get_norm_term_variations(term)
        if len(norm_terms) == 0:
            return []

        # Generate a unique identifier to be used for storing intermediate results. This is to
        # prevent redis key collisions between competing suggest / exact_suggest calls.
        uuid_str = str(uuid.uuid4())
        intermediate_result_key = RESULT_SET_BASE_NAME % (uuid_str,)

        # Get the matched result IDs
        pipe = REDIS.pipeline()
        for provider in providers:
            provider_name = provider.provider_name

            MAX_RESULTS = registry.get_ac_provider_setting(self.name, provider, 'MAX_RESULTS')
            keys = []
            for norm_term in norm_terms:
                keys.append(EXACT_BASE_NAME % (provider_name, norm_term,))
            # Do not attempt zunionstore on empty list because redis errors out.
            if len(keys) == 0:
                continue
            pipe.zunionstore(intermediate_result_key, keys, aggregate='MIN')
            pipe.zrange(intermediate_result_key, 0, MAX_RESULTS - 1)
            pipe.delete(intermediate_result_key)
        results = [i for i in pipe.execute() if type(i) == list]

        # Create a dict mapping provider to result IDs
        for provider in providers:
            provider_name = provider.provider_name

            MAX_RESULTS = registry.get_ac_provider_setting(self.name, provider, 'MAX_RESULTS')
            exact_ids = results.pop(0)
            provider_results[provider_name] = exact_ids[:MAX_RESULTS]

        results = self._get_results_from_ids(provider_results)

        # If told to, cache the final results for CACHE_TIMEOUT secnds
        if settings.CACHE_TIMEOUT:
            REDIS.setex(cache_key, self.__class__._serialize_data(results), settings.CACHE_TIMEOUT)
        return results

    def _get_results_from_ids(self, provider_results):
        """
        Given a dict mapping providers to results IDs, return
        a dict mapping providers to results
        """
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
                    [self.__class__._deserialize_data(i) for i in results.pop(0) if i is not None]

        if settings.FLATTEN_SINGLE_TYPE_RESULTS and len(provider_results) == 1:
            provider_results = list(provider_results.values())[0]
        return provider_results

    def _get_all_providers_by_autocompleter(self):
        return registry.get_all_by_autocompleter(self.name)
