import itertools
import json
import logging
import uuid
from collections import OrderedDict
from hashlib import sha1

import redis

from autocompleter import registry, settings, utils

REDIS = redis.Redis(
    host=settings.REDIS_CONNECTION["host"],
    port=settings.REDIS_CONNECTION["port"],
    db=settings.REDIS_CONNECTION["db"],
)

if settings.TEST_DATA:
    AUTO_BASE_NAME = "djac.test.%s"
    RESULT_SET_BASE_NAME = "djac.test.results.%s"

else:
    AUTO_BASE_NAME = "djac.%s"
    RESULT_SET_BASE_NAME = "djac.results.%s"

CACHE_BASE_NAME = AUTO_BASE_NAME + ".c.%s.%s"
EXACT_CACHE_BASE_NAME = AUTO_BASE_NAME + ".ce.%s"

PREFIX_BASE_NAME = AUTO_BASE_NAME + ".p.%s"
PREFIX_SET_BASE_NAME = AUTO_BASE_NAME + ".ps"

EXACT_BASE_NAME = AUTO_BASE_NAME + ".e.%s"
EXACT_SET_BASE_NAME = AUTO_BASE_NAME + ".es"

TERM_MAP_BASE_NAME = AUTO_BASE_NAME + ".tm"

FACET_BASE_NAME = AUTO_BASE_NAME + ".f"
FACET_SET_BASE_NAME = FACET_BASE_NAME + ".%s.%s"
FACET_MAP_BASE_NAME = AUTO_BASE_NAME + ".fm"

RESULT_SET_BASE_NAME = "djac.results.%s"

SCORE_MAP_BASE_NAME = AUTO_BASE_NAME + ".sm"


class AutocompleterBase(object):
    def __init__(self, logger=None) -> None:
        self.log = logger if logger else logging.getLogger()

    @classmethod
    def _serialize_data(cls, data):
        return json.dumps(data)

    @classmethod
    def _deserialize_data(cls, raw):
        # The scores that are inserted into Redis are actually 1/score. On the other hand, we
        # have securities which have their score set to 0. When that happens, we store the score
        # as inf, which Redis knows about and can handle, but the JSON spec does not so we get
        # an error when trying to deserialize it.
        # Here, we check to see if the redis stored value is b"inf" and only deserialize it when it's
        # not. If it is, we leave it as "inf"

        return json.loads(raw.decode("utf-8")) if raw != b"inf" else "inf"

    @staticmethod
    def _get_prefixes_set(norm_terms_list):
        """
        Returns the set of all prefixes from a list of norm terms.
        A set is used in order to avoid duplications, since these are fairly common with prefixes.
        """
        return {
            word[:x]
            for norm_term in norm_terms_list
            for word in norm_term.split(" ")
            for x in range(1, len(word) + 1)
        }


class AutocompleterProviderBase(AutocompleterBase):
    # Name in redis that data for this provider will be stored. To preserve memory, keep this short.
    provider_name = None
    # Cache of all aliases for this provider, including all possible variations
    _phrase_aliases = None

    def __init__(self, obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        # objects returned in alphabetical order when they have the same score.
        score = self.get_score()
        try:
            score = 1 / float(score)
        except ZeroDivisionError:
            score = float("inf")
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
                norm_terms_with_variations = (
                    norm_terms_with_variations
                    + utils.get_aliased_variations(norm_term, phrase_aliases)
                )

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

        norm_phrase_aliases = utils.build_norm_phrase_alias_dict(
            cls.get_phrase_aliases()
        )
        one_way_phrase_aliases = cls.get_one_way_phrase_aliases()
        one_way_norm_phrase_aliases = utils.build_norm_phrase_alias_dict(
            one_way_phrase_aliases, two_way=False
        )

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
    def get_old_norm_terms(cls, obj_id):
        key = TERM_MAP_BASE_NAME % (cls.get_provider_name(),)
        old_terms = REDIS.hget(key, obj_id)
        if old_terms is not None:
            old_terms = cls._deserialize_data(old_terms)
        return old_terms

    @classmethod
    def get_old_facets(cls, obj_id):
        facet_map_name = FACET_MAP_BASE_NAME % (cls.get_provider_name(),)
        old_facets = REDIS.hget(facet_map_name, obj_id)
        if old_facets is not None:
            old_facets = cls._deserialize_data(old_facets)
        return old_facets

    @classmethod
    def get_old_score(cls, obj_id):
        score_map_name = SCORE_MAP_BASE_NAME % (cls.get_provider_name(),)
        old_score = REDIS.hget(score_map_name, obj_id)
        if old_score is not None:
            old_score = cls._deserialize_data(old_score)
        return old_score

    @classmethod
    def clear_facets(cls, obj_id, old_facets):
        """
        For a given object ID, delete old facet data from Redis.
        """
        provider_name = cls.get_provider_name()
        pipe = REDIS.pipeline()
        # Remove old facets from the corresponding facet sorted set containing scores
        for facet in old_facets:
            try:
                facet_name = facet["key"]
                facet_value = facet["value"]
                facet_set_name = FACET_SET_BASE_NAME % (
                    provider_name,
                    facet_name,
                    facet_value,
                )
                pipe.zrem(facet_set_name, obj_id)
            except KeyError:
                continue
        # Now delete the mapping from obj_id -> facets
        facet_map_name = FACET_MAP_BASE_NAME % (provider_name,)
        pipe.hdel(facet_map_name, obj_id)

        # End pipeline
        pipe.execute()

    @classmethod
    def clear_keys(cls, obj_id, old_norm_terms):
        """
        For a given object ID, delete old norm terms from Redis.
        """
        provider_name = cls.get_provider_name()
        # Start pipeline
        pipe = REDIS.pipeline()
        # Processes prefixes of object, removing object ID from sorted sets
        for norm_term in old_norm_terms:
            norm_words = norm_term.split(" ")
            for norm_word in norm_words:
                word_prefix = ""
                for char in norm_word:
                    word_prefix += char
                    key = PREFIX_BASE_NAME % (
                        provider_name,
                        word_prefix,
                    )
                    pipe.zrem(key, obj_id)

                    key = PREFIX_SET_BASE_NAME % (provider_name,)
                    pipe.srem(key, word_prefix)

        # Process normalized terms of object, removing object ID from a sorted set
        # representing exact matches
        for norm_term in old_norm_terms:
            key = EXACT_BASE_NAME % (
                provider_name,
                norm_term,
            )
            pipe.zrem(key, obj_id)

            key = EXACT_SET_BASE_NAME % (provider_name,)
            pipe.srem(key, norm_term)

        # Remove model ID to data mapping
        key = AUTO_BASE_NAME % (provider_name,)
        pipe.hdel(key, obj_id)

        # Remove obj_id to terms mapping
        key = TERM_MAP_BASE_NAME % (provider_name,)
        pipe.hdel(key, obj_id)

        # End pipeline
        pipe.execute()

    @classmethod
    def clear_score(cls, obj_id):
        """
        For a given object ID, delete old score from Redis.
        """
        provider_name = cls.get_provider_name()
        pipe = REDIS.pipeline()
        # Delete the mapping from obj_id -> score
        scores_map_name = SCORE_MAP_BASE_NAME % (provider_name,)
        pipe.hdel(scores_map_name, obj_id)

        # End pipeline
        pipe.execute()

    @classmethod
    def get_facets(cls):
        """
        Facets are extra properties users can define to help further filter suggest results.
        Should be a list of identifiers, where each identifier can be found as a key in the
        dictionary returned by get_data.
        """
        return []

    def get_facets_dict(self):
        """
        Returns a list of facet dicts.

        Each facet dict is of the form {"key": <facet-name>, "value": <facet-value>}
        """
        facet_dicts = []
        data = self.get_data()
        for facet in self.get_facets():
            try:
                facet_dicts.append({"key": facet, "value": data[facet]})
            except KeyError:
                pass
        return facet_dicts

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
        provider_name = self.get_provider_name()
        obj_id = self.get_item_id()
        terms = self.get_terms()
        norm_terms = self.__class__._get_norm_terms(terms)
        score = self._get_score()
        data = self.get_data()
        facets = self.get_facets()

        # Get all the facet values from the data dict
        facet_dicts = self.get_facets_dict()

        old_norm_terms = self.__class__.get_old_norm_terms(obj_id)
        old_facets = self.__class__.get_old_facets(obj_id)
        old_score = self.__class__.get_old_score(obj_id)

        norm_terms_updated = norm_terms != old_norm_terms
        facets_updated = facets != old_facets
        score_updated = score != old_score

        # Check if the terms or facets have been updated. If both weren't updated,
        # then we can just update the data payload and short circuit.
        if not norm_terms_updated and not facets_updated:
            # Store obj ID to data mapping
            key = AUTO_BASE_NAME % (provider_name,)
            REDIS.hset(key, obj_id, self.__class__._serialize_data(data))
            return

        # Clear out the obj_id's old data if told to
        if delete_old is True:
            # TODO: memoize get_old_terms? Otherwise have to pass old_terms down the line to avoid
            # doing 2 extra redis queries.
            if norm_terms_updated and old_norm_terms is not None:
                self.__class__.clear_keys(obj_id, old_norm_terms)
            if facets_updated and old_facets is not None:
                self.__class__.clear_facets(obj_id, old_facets)
            if score_updated and old_score is not None:
                self.__class__.clear_score(obj_id)

        # Start pipeline
        pipe = REDIS.pipeline()

        # Processes prefixes of object, placing object ID in sorted sets
        for word_prefix in self._get_prefixes_set(norm_terms):
            # Store prefix to obj ID mapping, with score
            key = PREFIX_BASE_NAME % (
                provider_name,
                word_prefix,
            )
            pipe.zadd(key, {obj_id: score})
            # Store autocompleter to prefix mapping so we know all prefixes
            # of an autocompleter
            key = PREFIX_SET_BASE_NAME % (provider_name,)
            pipe.sadd(key, word_prefix)

        # Process normalized term of object, placing object ID in a sorted set
        # representing exact matches
        max_exact_match_words = registry.get_provider_setting(
            self, "MAX_EXACT_MATCH_WORDS"
        )
        if max_exact_match_words > 0:
            for norm_term in norm_terms:
                if len(norm_term.split(" ")) > max_exact_match_words:
                    continue
                # Store exact term to obj ID mapping, with score
                key = EXACT_BASE_NAME % (
                    provider_name,
                    norm_term,
                )
                pipe.zadd(key, {obj_id: score})

                # Store autocompleter to exact term mapping so we know all exact terms
                # of an autocompleter
                key = EXACT_SET_BASE_NAME % (provider_name,)
                pipe.sadd(key, norm_term)

        for facet in facet_dicts:
            key = FACET_SET_BASE_NAME % (
                provider_name,
                facet["key"],
                facet["value"],
            )
            pipe.zadd(key, {obj_id: score})

        # Map provider's obj_id -> data payload
        key = AUTO_BASE_NAME % (provider_name,)
        pipe.hset(key, obj_id, self.__class__._serialize_data(data))

        # Map provider's obj_id -> norm terms list
        key = TERM_MAP_BASE_NAME % (provider_name,)
        pipe.hset(key, obj_id, self.__class__._serialize_data(norm_terms))

        # Map provider's obj_id -> facet data
        if len(facet_dicts) > 0:
            key = FACET_MAP_BASE_NAME % (provider_name,)
            pipe.hset(key, obj_id, self.__class__._serialize_data(facet_dicts))

        # Map provider's obj_id -> score value
        key = SCORE_MAP_BASE_NAME % (provider_name,)
        pipe.hset(key, obj_id, score)

        # End pipeline
        pipe.execute()

    def remove(self):
        """
        Remove an object from the autocompleter
        DO NOT override this.
        """
        # Init data
        obj_id = self.get_item_id()
        terms = self.__class__.get_old_norm_terms(obj_id)
        if terms is not None:
            self.__class__.clear_keys(obj_id, terms)
        facets = self.__class__.get_old_facets(obj_id)
        if facets is not None:
            self.__class__.clear_facets(obj_id, facets)
        self.__class__.clear_score(obj_id)


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

    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
                provider = provider_class(obj)
                if provider.include_item():
                    provider.store(delete_old=delete_old)

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
            keys = [
                PREFIX_BASE_NAME
                % (
                    provider_name,
                    prefix.decode(),
                )
                for prefix in prefixes
            ]
            chunked_prefix_keys = self.chunk_list(keys, 100)

            # Get list of all exact match terms for autocompleter
            exact_set_name = EXACT_SET_BASE_NAME % (provider_name,)
            norm_terms = REDIS.smembers(exact_set_name)
            keys = [
                EXACT_BASE_NAME
                % (
                    provider_name,
                    norm_term.decode(),
                )
                for norm_term in norm_terms
            ]
            chunked_norm_term_keys = self.chunk_list(keys, 100)

            # Get list of facets
            facet_base = FACET_BASE_NAME % (provider_name,)
            keys = [facet.decode() for facet in REDIS.keys(facet_base + ".*")]
            facet_keys = self.chunk_list(keys, 100)

            # Start pipeline
            pipe = REDIS.pipeline()

            # For each prefix, delete sorted set (in groups of 100)
            for chunk in chunked_prefix_keys:
                pipe.delete(*chunk)
            # Delete the set of prefixes
            pipe.delete(prefix_set_name)

            # For each exact match term, delete sorted set (in groups of 100
            for chunk in chunked_norm_term_keys:
                pipe.delete(*chunk)
            # Delete the set of exact matches
            pipe.delete(exact_set_name)

            # For each facet, delete sorted set (in groups of 100)
            for chunk in facet_keys:
                pipe.delete(*chunk)
            # Delete the facet mapping
            facet_map_name = FACET_MAP_BASE_NAME % (provider_name,)
            pipe.delete(facet_map_name)

            # Remove provider's obj_id -> data payload mapping
            key = AUTO_BASE_NAME % (provider_name,)
            pipe.delete(key)

            # Remove provider's obj_id -> norm terms mapping
            key = TERM_MAP_BASE_NAME % (provider_name,)
            pipe.delete(key)

            # Remove provider's obj_id -> score mapping
            key = SCORE_MAP_BASE_NAME % (provider_name,)
            pipe.delete(key)

            # End pipeline
            pipe.execute()

            # There is a possibility that some straggling keys have not been
            # cleaned up if their ID changed but for some reason we did not
            # delete the old ID... Here we delete what's left, just to be safe.

            # However in our controlled testing environment, we should be perfect so
            # this clean up should not be necessary, and if it is it means something real is wrong.
            if not settings.TEST_DATA:
                key = AUTO_BASE_NAME % (provider_name,)
                key += "*"
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
        cache_key = CACHE_BASE_NAME % (self.name, "*", "*")
        exact_cache_key = EXACT_CACHE_BASE_NAME % (
            self.name,
            "*",
        )

        keys = REDIS.keys(cache_key) + REDIS.keys(exact_cache_key)
        if len(keys) > 0:
            REDIS.delete(*keys)

    def suggest(self, term, facets=[]):
        """
        Suggest matching objects, given a term
        """
        providers = self._get_all_providers_by_autocompleter()
        if providers is None:
            return []

        # If we have a cached version of the search results available, return it!
        hashed_facets = self.hash_facets(facets)
        cache_key = CACHE_BASE_NAME % (
            self.name,
            utils.get_normalized_term(term, settings.JOIN_CHARS),
            hashed_facets,
        )
        if settings.CACHE_TIMEOUT and REDIS.exists(cache_key):
            return self.__class__._deserialize_data(REDIS.get(cache_key))

        # Get the normalized term variations we need to search for each term. A single term
        # could turn into multiple terms we need to search.
        norm_terms = utils.get_norm_term_variations(term)
        if len(norm_terms) == 0:
            return []

        provider_results = OrderedDict()

        # Generate a unique identifier to be used for storing intermediate results. This is to
        # prevent redis key collisions between competing suggest / exact_suggest calls.
        base_result_key = RESULT_SET_BASE_NAME % str(uuid.uuid4())
        base_exact_match_key = RESULT_SET_BASE_NAME % str(uuid.uuid4())
        # Same idea as the base_result_key, but for when we are using facets in the suggest call.
        facet_final_result_key = RESULT_SET_BASE_NAME % str(uuid.uuid4())
        facet_final_exact_match_key = RESULT_SET_BASE_NAME % str(uuid.uuid4())
        # As we search, we may store a number of intermediate data items. We keep track of
        # what we store and delete so there is nothing left over
        # We initialize with the base keys all of which could end up being used.
        keys_to_delete = {
            base_result_key,
            base_exact_match_key,
            facet_final_result_key,
            facet_final_exact_match_key,
        }

        facet_keys_set = set()
        if len(facets) > 0:
            # we use from_iterable to flatten the list comprehension into a single list
            sub_facets = itertools.chain.from_iterable(
                [facet["facets"] for facet in facets]
            )
            facet_keys_set = set([sub_facet["key"] for sub_facet in sub_facets])

        MOVE_EXACT_MATCHES_TO_TOP = registry.get_autocompleter_setting(
            self.name, "MOVE_EXACT_MATCHES_TO_TOP"
        )
        # Get the max results autocompleter setting
        MAX_RESULTS = registry.get_autocompleter_setting(self.name, "MAX_RESULTS")

        pipe = REDIS.pipeline()
        for provider in providers:
            provider_name = provider.provider_name

            # If the total length of the term is less than MIN_LETTERS allowed, then don't search
            # the provider for this term
            MIN_LETTERS = registry.get_ac_provider_setting(
                self.name, provider, "MIN_LETTERS"
            )
            if len(term) < MIN_LETTERS:
                continue

            term_result_keys = []
            for norm_term in norm_terms:
                norm_words = norm_term.split()
                keys = [
                    PREFIX_BASE_NAME
                    % (
                        provider_name,
                        norm_word,
                    )
                    for norm_word in norm_words
                ]
                if len(keys) == 1:
                    term_result_keys.append(keys[0])
                else:
                    term_result_key = base_result_key + "." + norm_term
                    term_result_keys.append(term_result_key)
                    keys_to_delete.add(term_result_key)
                    pipe.zinterstore(term_result_key, keys, aggregate="MIN")

            if len(term_result_keys) == 1:
                final_result_key = term_result_keys[0]
            else:
                final_result_key = base_result_key
                pipe.zunionstore(final_result_key, term_result_keys, aggregate="MIN")

            use_facets = False
            if len(facet_keys_set) > 0:
                provider_keys_set = set(provider.get_facets())
                if facet_keys_set.issubset(provider_keys_set):
                    use_facets = True

            if use_facets:
                facet_result_keys = []
                for facet in facets:
                    try:
                        facet_type = facet["type"]
                        if facet_type not in ["and", "or"]:
                            continue
                        facet_list = facet["facets"]
                        facet_set_keys = []
                        for facet_dict in facet_list:
                            facet_set_key = FACET_SET_BASE_NAME % (
                                provider_name,
                                facet_dict["key"],
                                facet_dict["value"],
                            )
                            facet_set_keys.append(facet_set_key)

                        if len(facet_set_keys) == 1:
                            facet_result_keys.append(facet_set_keys[0])
                        else:
                            facet_result_key = RESULT_SET_BASE_NAME % str(uuid.uuid4())
                            facet_result_keys.append(facet_result_key)
                            keys_to_delete.add(facet_result_key)
                            if facet_type == "and":
                                pipe.zinterstore(
                                    facet_result_key, facet_set_keys, aggregate="MIN"
                                )
                            else:
                                pipe.zunionstore(
                                    facet_result_key, facet_set_keys, aggregate="MIN"
                                )
                    except KeyError:
                        continue

                # We want to calculate the intersection of all the intermediate facet sets created so far
                # along with the final result set. So we append the final_result_key to the list of
                # facet_result_keys and store the intersection in the faceted final result set.
                pipe.zinterstore(
                    facet_final_result_key,
                    facet_result_keys + [final_result_key],
                    aggregate="MIN",
                )

            if use_facets:
                pipe.zrange(facet_final_result_key, 0, MAX_RESULTS - 1)
            else:
                pipe.zrange(final_result_key, 0, MAX_RESULTS - 1)

            # Get exact matches
            if MOVE_EXACT_MATCHES_TO_TOP:
                keys = []
                for norm_term in norm_terms:
                    keys.append(
                        EXACT_BASE_NAME
                        % (
                            provider_name,
                            norm_term,
                        )
                    )
                # Do not attempt zunionstore on empty list because redis errors out.
                if len(keys) == 0:
                    continue

                if len(keys) == 1:
                    final_exact_match_key = keys[0]
                else:
                    final_exact_match_key = base_exact_match_key
                    pipe.zunionstore(final_exact_match_key, keys, aggregate="MIN")

                # If facets are being used for this suggest call, we need to make sure that
                # exact term matches don't bypass the requirement of having matching facet values.
                # To achieve this, we intersect all faceted matches (exact-and-non-exact) with
                # all exact matches.
                if use_facets:
                    pipe.zinterstore(
                        facet_final_exact_match_key,
                        facet_result_keys + [final_exact_match_key],
                        aggregate="MIN",
                    )
                    pipe.zrange(facet_final_exact_match_key, 0, MAX_RESULTS - 1)
                else:
                    pipe.zrange(final_exact_match_key, 0, MAX_RESULTS - 1)

        pipe.delete(*keys_to_delete)

        results = [i for i in pipe.execute() if type(i) == list]

        # Total number of results currently allocated to providers
        total_allocated_results = 0
        # Maximum number of results allowed per provider
        provider_max_results = OrderedDict()

        # Get an initial max/provider based on a equal share of MAX_RESULTS
        for provider in providers:
            provider_name = provider.provider_name
            results_per_provider = self.normalize_rounding(MAX_RESULTS / len(providers))
            provider_max_results[provider_name] = results_per_provider
            total_allocated_results += results_per_provider

        # Due to having to round to nearest result, the maximum number of results
        # allocated could be less/more than the max allowed... Here we adjust providers
        # results until total allocation equals max allowed
        diff = 1 if total_allocated_results < MAX_RESULTS else -1
        while total_allocated_results != MAX_RESULTS:
            for provider in providers:
                provider_name = provider.provider_name
                provider_max_results[provider_name] += diff
                total_allocated_results += diff
                if total_allocated_results == MAX_RESULTS:
                    break

        # Result IDs per provider
        provider_result_ids = OrderedDict()
        # Number of results we will be getting from each provider
        provider_num_results = OrderedDict()
        # Total pool of extra result slots
        total_surplus = 0
        # Number of extra result slots a provider could use
        provider_deficits = OrderedDict()

        # Create a dict mapping provider to number of result IDs available
        # We combine the 2 different kinds of results into 1 result ID list per provider.
        # Also keep track of number of extra result slots available when a provider does not
        # use up its allocated slots.
        for provider in providers:
            provider_name = provider.provider_name

            # If the total length of the term is less than MIN_LETTERS allowed, then don't search
            # the provider for this term
            MIN_LETTERS = registry.get_ac_provider_setting(
                self.name, provider, "MIN_LETTERS"
            )
            if len(term) < MIN_LETTERS:
                # if provider will not be used due to min_letters, put all result slots
                # in surplus pool then continue
                total_surplus += provider_max_results[provider_name]
                continue

            ids = results.pop(0)
            # We merge exact matches with base matches by moving them to
            # the head of the results
            if MOVE_EXACT_MATCHES_TO_TOP:
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
            surplus = provider_max_results[provider_name] - len(ids)
            if surplus >= 0:
                provider_num_results[provider_name] = len(ids)
                total_surplus += surplus
            else:
                # create base usage
                provider_num_results[provider_name] = provider_max_results[
                    provider_name
                ]
                # create dict of how many extra each provider actually needs
                provider_deficits[provider_name] = -surplus

        # If there are extra result slots available, go through each provider that
        # needs extra results, and hand them out until there are no more to give
        while total_surplus > 0:
            # Check if there are any providers that still need extra results, and if not exit the loop,
            # else we get caught in an infinite loop
            provider_with_deficit_exists = False
            for provider_name in provider_deficits:
                deficit = provider_deficits[provider_name]
                if deficit > 0:
                    provider_with_deficit_exists = True
            if not provider_with_deficit_exists:
                break
            for provider_name in provider_deficits:
                deficit = provider_deficits[provider_name]
                if deficit > 0:
                    provider_num_results[provider_name] += 1
                    provider_deficits[provider_name] -= 1
                    total_surplus -= 1

                if total_surplus <= 0:
                    break

        # At this point we should have the final number of results we will be getting
        # from each provider, so we get from provider and put in final result IDs dict
        for provider in providers:
            provider_name = provider.provider_name
            try:
                num_results = provider_num_results[provider_name]
                provider_results[provider_name] = provider_result_ids[provider][
                    :num_results
                ]
            except KeyError:
                continue

        results = self._get_results_from_ids(provider_results)

        # If told to, cache the final results for CACHE_TIMEOUT secnds
        if settings.CACHE_TIMEOUT:
            REDIS.setex(
                cache_key,
                settings.CACHE_TIMEOUT,
                self.__class__._serialize_data(results),
            )
        return results

    def exact_suggest(self, term):
        """
        Suggest matching objects exacting matching term given, given a term
        """
        providers = self._get_all_providers_by_autocompleter()
        if providers is None:
            return []

        # If we have a cached version of the search results available, return it!
        cache_key = EXACT_CACHE_BASE_NAME % (
            self.name,
            term,
        )
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

        MAX_RESULTS = registry.get_autocompleter_setting(self.name, "MAX_RESULTS")

        # Get the matched result IDs
        pipe = REDIS.pipeline()
        for provider in providers:
            provider_name = provider.provider_name
            keys = []
            for norm_term in norm_terms:
                keys.append(
                    EXACT_BASE_NAME
                    % (
                        provider_name,
                        norm_term,
                    )
                )
            # Do not attempt zunionstore on empty list because redis errors out.
            if len(keys) == 0:
                continue
            pipe.zunionstore(intermediate_result_key, keys, aggregate="MIN")
            pipe.zrange(intermediate_result_key, 0, MAX_RESULTS - 1)
            pipe.delete(intermediate_result_key)
        results = [i for i in pipe.execute() if type(i) == list]

        # Create a dict mapping provider to result IDs
        for provider in providers:
            provider_name = provider.provider_name
            exact_ids = results.pop(0)
            provider_results[provider_name] = exact_ids[:MAX_RESULTS]

        results = self._get_results_from_ids(provider_results)

        # If told to, cache the final results for CACHE_TIMEOUT seconds
        if settings.CACHE_TIMEOUT:
            REDIS.setex(
                cache_key,
                settings.CACHE_TIMEOUT,
                self.__class__._serialize_data(results),
            )
        return results

    def get_provider_result_from_id(self, provider_name, object_id):
        """
        Given a `provider_name` and `id`, return the corresponding redis payload.
        """
        results = self._get_results_from_ids({provider_name: [object_id]})
        try:
            if isinstance(results, list):
                result = results[0]
            else:
                result = list(filter(None, results.values()))[0][0]
        except IndexError:
            result = {}
        return result

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

        # Put them in the  provider results dict
        for provider_name, ids in provider_results.items():
            if len(ids) > 0:
                provider_results[provider_name] = [
                    self.__class__._deserialize_data(i)
                    for i in results.pop(0)
                    if i is not None
                ]

        if settings.FLATTEN_SINGLE_TYPE_RESULTS and len(provider_results) == 1:
            provider_results = list(provider_results.values())[0]
        return provider_results

    def _get_all_providers_by_autocompleter(self):
        return registry.get_all_by_autocompleter(self.name)

    @staticmethod
    def chunk_list(lst, chunk_size):
        """
        Given list, return a list of lists where each sublist is of  size chunk_size or less.

        :param lst: list to break up into chunks
        :type lst: lst
        :param chunk_size: size of each chunk
        :type chunk_size: int
        """
        for i in range(0, len(lst), chunk_size):
            yield lst[i : i + chunk_size]

    @staticmethod
    def hash_facets(facets):
        """
        Given an array of facet data, return a deterministic hash such that
        the ordering of keys inside the facet dicts does not matter.
        """

        def sha1_digest(my_str):
            return sha1(my_str.encode(encoding="UTF-8")).hexdigest()

        facet_hashes = []
        for facet in facets:
            sub_facet_hashes = []
            facet_type = facet["type"]
            sub_facets = facet["facets"]
            for sub_facet in sub_facets:
                sub_facet_str = (
                    "key:" + sub_facet["key"] + "value:" + str(sub_facet["value"])
                )
                sub_facet_hashes.append(sha1_digest(sub_facet_str))
            sub_facet_hashes.sort()
            facet_str = "type:" + facet_type + "facets:" + str(sub_facet_hashes)
            facet_hashes.append(sha1_digest(facet_str))
        facet_hashes.sort()
        final_facet_hash = sha1_digest(str(facet_hashes))
        return final_facet_hash

    @staticmethod
    def normalize_rounding(value):
        """
        Python 2 and Python 3 handing the rounding of halves (0.5, 1.5, etc) differently.
        Stick to Python 2 version of rounding to be consistent.
        """
        if not isinstance(value, (int, float)):
            raise ValueError(
                "Value to round must be an int or float, not %s." % type(value).__name__
            )
        if round(0.5) != 1 and value % 1 == 0.5 and not int(value) % 2:
            return int((round(value) + (abs(value) / value) * 1))
        else:
            return int(round(value))

    def update_all(self, clear_cache=True):
        """
        Update all modified objects within all the ac's providers
        """
        for provider_class in self._get_all_providers_by_autocompleter():
            self.update_provider(provider_class)
        if clear_cache:
            self.clear_cache()

    def update_provider(self, provider_class):
        """
        Update all modified objects within a provider.

        Only objects or objects' properties that were added and removed are dealt with, leaving the
        rest untouched.  Updates to an object are understood as an addition of the new value and
        removal of the old value.

        This method attempts to optimize the number of operations done on the Redis DB. The overall
        strategy for this is to create mappings (for quick references) and sets (for quick
        comparisons) and pre-process operations as much as possible before hitting the DB. This method
        has 6 different parts:
        1. PROCESS LIVE DATA: Goes through current data and processes it
        2. PREPARE DATA STRUCTURES: Initializes the main data structures that will be used througout the method
        3. TERMS AND PREFIXES: Updates to hash maps and sets related to exact terms and term prefixes
        4. FACETS: Updates to ZSET djac.provider.f.key.value and HASH djac.provider.fm
        5. DATA: Updates to HASH djac.provider
        6. SCORES: Updates to HASH djac.provider.sm

        Throughout the method, the different data structures variables use the following convention:
                             <data>_<origin>_<data_structure>
        where:
        * <data> - the actual data being stored: terms, facets, score or data
        * <origin> - where the data was taken from: live means current data and db means stored in redis
        * <data_structure> - data structure used to hold the data: either map or set
        """

        def _facet_list_to_set(facet_list):
            return frozenset((f["key"], f["value"]) for f in facet_list)

        provider_name = provider_class.get_provider_name()
        self.log.info(f"Start update of provider {provider_name}")
        scores_live_map = dict()
        facets_live_map = dict()
        terms_live_map = dict()
        data_live_map = dict()
        pipe = REDIS.pipeline()

        ###################
        # PROCESS LIVE DATA
        ###################
        # Iterate over all objects fetching the live data
        for obj in provider_class.get_iterator():
            provider = provider_class(obj)
            obj_id = str(provider.get_item_id())
            data = provider.get_data()
            data_live_map[obj_id] = data

            # Maintain a mapping of each obj's score for later insertion into the sorted sets
            scores_live_map[obj_id] = provider._get_score()

            # Maintain a mapping of each obj's norm terms
            terms = provider.get_terms()
            norm_terms = provider.__class__._get_norm_terms(terms) or []
            terms_live_map[obj_id] = norm_terms

            # Maintain a mapping of each obj's facets list of dicts
            facets_live_map[obj_id] = provider.get_facets_dict()

        ##########################
        # PREPARE DATA STRUCTURES
        ##########################
        terms_map_key = TERM_MAP_BASE_NAME % provider_name
        # Fetch all terms from the DB in a single query and build a map of them with obj_id as key
        terms_db_map = {
            str(obj_id.decode("utf-8")): self._deserialize_data(terms)
            for obj_id, terms in REDIS.hgetall(terms_map_key).items()
        }

        # Build the terms into sets for quick comparisons
        terms_db_set = {
            (obj_id, frozenset(terms)) for obj_id, terms in terms_db_map.items()
        }
        terms_live_set = {
            (obj_id, frozenset(terms)) for obj_id, terms in terms_live_map.items()
        }
        # Build the prefixes into sets for quick comparisons
        prefixes_db_set = {
            (obj_id, frozenset(self._get_prefixes_set(norm_terms)))
            for obj_id, norm_terms in terms_db_map.items()
        }
        prefixes_live_set = {
            (obj_id, frozenset(self._get_prefixes_set(norm_terms)))
            for obj_id, norm_terms in terms_live_map.items()
        }
        # Fetch all the facets in the DB in a single query.
        facet_map_key = FACET_MAP_BASE_NAME % provider_name
        facets_db_map = {
            str(obj_id.decode("utf-8")): self._deserialize_data(facets)
            for obj_id, facets in REDIS.hgetall(facet_map_key).items()
        }

        # Build the facets maps into sets for quick comparisons
        facets_live_set = {
            (obj_id, _facet_list_to_set(list_of_dicts))
            for obj_id, list_of_dicts in facets_live_map.items()
        }
        facets_db_set = {
            (obj_id, _facet_list_to_set(list_of_dicts))
            for obj_id, list_of_dicts in facets_db_map.items()
        }
        # Build a set with the obj_ids of objects that updated their score.
        # These will need to be updated in all the ZSETs
        scores_map_key = SCORE_MAP_BASE_NAME % provider_name
        scores_db_map = {}
        for obj_id, score in REDIS.hgetall(scores_map_key).items():
            parsed_score = self._deserialize_data(score)
            obj_id = str(obj_id.decode("utf-8"))
            scores_db_map[obj_id] = float(parsed_score)

        objs_with_updated_scores = {
            obj_id
            for obj_id, score in scores_live_map.items()
            if scores_db_map.get(obj_id) != score
        }

        #####################
        # TERMS AND PREFIXES
        #####################
        max_word_count = registry.get_provider_setting(
            provider, "MAX_EXACT_MATCH_WORDS"
        )
        objs_with_updated_terms = {
            obj_id for obj_id, _ in terms_live_set ^ terms_db_set
        }
        for obj_id in objs_with_updated_terms | objs_with_updated_scores:
            # Symmetric difference tells us which objects need to be updated but we don't know
            # which element comes from which set, so we retrieve the terms from the terms mappings to
            # compare them
            live_obj_terms = frozenset(terms_live_map.get(obj_id, []))
            db_obj_terms = frozenset(terms_db_map.get(obj_id, []))

            # Terms in the live set but not in the DB are new terms
            # But if the obj's score changed, we want to update all the terms
            terms_to_add = (
                live_obj_terms
                if obj_id in objs_with_updated_scores
                else live_obj_terms - db_obj_terms
            )
            for term in terms_to_add:
                # Terms only get added if there are less than MAX_EXACT_MATCH_WORDS words
                if len(term.split(" ")) <= max_word_count:
                    exact_sorted_set_key = EXACT_BASE_NAME % (provider_name, term)
                    pipe.zadd(exact_sorted_set_key, {obj_id: scores_live_map[obj_id]})
            self.log.info(f"Added {len(terms_to_add)} entries to {EXACT_BASE_NAME}")
            # Terms in tterms_to_removehe DB but not in the live set are terms that got removed
            terms_to_remove = db_obj_terms - live_obj_terms
            for term in terms_to_remove:
                exact_sorted_set_key = EXACT_BASE_NAME % (provider_name, term)
                pipe.zrem(exact_sorted_set_key, obj_id)
            self.log.info(
                f"Removed {len(terms_to_remove)} entries from {EXACT_BASE_NAME}"
            )

            # Repeat the same logic for prefixes
            live_obj_prefixes = frozenset(
                frozenset(self._get_prefixes_set(terms_live_map.get(obj_id, [])))
            )
            db_obj_prefixes = frozenset(
                frozenset(self._get_prefixes_set(terms_db_map.get(obj_id, [])))
            )
            # Prefixes in the live set but not in the DB are new prefixes found in its terms
            # But if the obj's score changed, we want to update all the prefixes
            prefixes_to_add = (
                live_obj_prefixes
                if obj_id in objs_with_updated_scores
                else live_obj_prefixes - db_obj_prefixes
            )
            for prefix in prefixes_to_add:
                prefix_sorted_set_key = PREFIX_BASE_NAME % (provider_name, prefix)
                pipe.zadd(prefix_sorted_set_key, {obj_id: scores_live_map[obj_id]})
            self.log.info(
                f"Added {len(prefixes_to_add)} entries to {prefix_sorted_set_key}"
            )

            # Prefixes in the DB but not in the live set are prefixes that got removed
            prefixes_to_remove = db_obj_prefixes - live_obj_prefixes
            for prefix in prefixes_to_remove:
                prefix_sorted_set_key = PREFIX_BASE_NAME % (provider_name, prefix)
                pipe.zrem(prefix_sorted_set_key, obj_id)
            self.log.info(
                f"Removed {len(prefixes_to_remove)} entries to {PREFIX_BASE_NAME}"
            )

        # Update exact terms sets
        # Build a single set of all terms in each data set
        all_terms_in_db = {x for _, term_set in terms_db_set for x in term_set}
        all_terms_in_live_data = {x for _, term_set in terms_live_set for x in term_set}
        exact_set_key = EXACT_SET_BASE_NAME % provider_name
        # Update the high-level set of exact terms in the provider in two operations
        if to_add := all_terms_in_live_data - all_terms_in_db:
            pipe.sadd(exact_set_key, *to_add)
            self.log.info(f"Added {len(to_add)} entries to {exact_set_key}")
        if to_remove := all_terms_in_db - all_terms_in_live_data:
            pipe.srem(exact_set_key, *to_remove)
            self.log.info(f"Removed {len(to_remove)} entries from {exact_set_key}")

        # Update the high-level hash map of terms in a single operation
        if to_add := terms_live_set - terms_db_set:
            mapping = {
                obj_id: self._serialize_data(terms_live_map[obj_id])
                for obj_id, _ in to_add
            }
            pipe.hset(terms_map_key, mapping=mapping)
            self.log.info(f"Added {len(mapping)} entries to {terms_map_key}")
        # Keys that are present in DB but not in the live data indicate objects
        # that were deleted. We remove them all in one operation
        if to_remove := set(terms_db_map.keys()) - set(terms_live_map.keys()):
            pipe.hdel(terms_map_key, *to_remove)
            self.log.info(f"Removed {len(to_remove)} entries from {terms_map_key}")

        # Update prefixes sets
        # Build a single set of all prefixes in each data set
        all_prefixes_in_db = {
            x for _, prefix_set in prefixes_db_set for x in prefix_set
        }
        all_prefixes_in_live_data = {
            x for _, prefix_set in prefixes_live_set for x in prefix_set
        }

        # Do relevant updates to high-level prefix set within the provider
        prefixes_set_key = PREFIX_SET_BASE_NAME % (provider_name,)
        if to_remove := all_prefixes_in_db - all_prefixes_in_live_data:
            pipe.srem(prefixes_set_key, *to_remove)
            self.log.info(f"Removed {len(to_remove)} entries from {prefixes_set_key}")
        if to_add := all_prefixes_in_live_data - all_prefixes_in_db:
            pipe.sadd(prefixes_set_key, *to_add)
            self.log.info(f"Added {len(to_remove)} entries to {prefixes_set_key}")

        #########
        # FACETS
        #########

        # Compare the two sets to get the updated objects
        objs_with_updated_facets = {
            obj_id for obj_id, _ in facets_live_set ^ facets_db_set
        }
        for obj_id in objs_with_updated_facets | objs_with_updated_scores:
            live_obj_facets = _facet_list_to_set(facets_live_map.get(obj_id, []))
            db_obj_facets = _facet_list_to_set(facets_db_map.get(obj_id, []))

            facets_to_add = (
                live_obj_facets
                if obj_id in objs_with_updated_scores
                else live_obj_facets - db_obj_facets
            )
            for key, value in facets_to_add:
                facet_sorted_set_key = FACET_SET_BASE_NAME % (provider_name, key, value)
                pipe.zadd(facet_sorted_set_key, {obj_id: scores_live_map[obj_id]})
            self.log.info(f"Added {len(facets_to_add)} entries to {FACET_BASE_NAME}")
            facets_to_remove = db_obj_facets - live_obj_facets
            for key, value in facets_to_remove:
                facet_sorted_set_key = FACET_SET_BASE_NAME % (provider_name, key, value)
                pipe.zrem(facet_sorted_set_key, obj_id)
            self.log.info(
                f"Removed {len(facets_to_remove)} entries to {FACET_SET_BASE_NAME}"
            )

        # Bulk update the facets hash map with all needed facets in a single operation
        if facets_with_updates := facets_live_set - facets_db_set:
            mapping = {
                obj_id: self._serialize_data(facets_live_map[obj_id])
                for obj_id, _ in facets_with_updates
            }
            pipe.hset(facet_map_key, mapping=mapping)
            self.log.info(f"Added {len(mapping)} entries to {facet_map_key}")

        # Keys that are present in DB but not in the live data indicate objects
        # that were deleted. We remove them all in one operation
        if obj_deleted := set(facets_db_map.keys()) - set(facets_live_map.keys()):
            pipe.hdel(facet_map_key, *obj_deleted)
            self.log.info(f"Removed {len(obj_deleted)} entries from {facet_map_key}")

        #######
        # DATA
        #######
        data_map_key = AUTO_BASE_NAME % provider_name
        data_db_map = {
            str(obj_id.decode("utf-8")): self._deserialize_data(data)
            for obj_id, data in REDIS.hgetall(data_map_key).items()
        }
        data_updated = {
            obj_id: self._serialize_data(data)
            for obj_id, data in data_live_map.items()
            if data != data_db_map.get(obj_id, {})
        }
        if data_updated:
            pipe.hset(data_map_key, mapping=data_updated)
            self.log.info(f"Added {len(data_updated)} entries to {data_map_key}")
        if objs_removed := set(data_db_map.keys()) - set(data_live_map.keys()):
            pipe.hdel(data_map_key, *objs_removed)
            self.log.info(f"Removed {len(objs_removed)} entries from {data_map_key}")

        #########
        # SCORES
        #########
        if updated_scores := {
            obj_id: scores_live_map[obj_id] for obj_id in objs_with_updated_scores
        }:
            pipe.hset(scores_map_key, mapping=updated_scores)
            self.log.info(f"Added {len(updated_scores)} entries to {scores_map_key}")
        if objs_removed := set(scores_db_map.keys()) - set(scores_live_map.keys()):
            pipe.hdel(scores_map_key, *objs_removed)
            self.log.info(f"Removed {len(objs_removed)} entries from {scores_map_key}")
        # Execute all the additions and deletions in a single connection
        pipe.execute()
        self.log.info(f"End update of provider {provider_name}")
