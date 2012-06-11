import hashlib
import redis

from django.utils.datastructures import SortedDict
from django.utils import simplejson

from autocompleter import registry, settings, utils

class AutocompleterProvider(object):
    _phrase_aliases = None

    provider_name = "main"

    def __init__(self, obj):
        self.obj = obj

    def get_obj_id(self):
        """
        The ID for the object, should be unique for each model. 
        Will normally not have to override this. However if model is such that
        lots of objects have the same score, autcompleter sorts lexographically by ID
        so it then helps to have this be a unique name representing the object instance
        to help make the sorting of the results make sense.
        i.e. for stock it might be stock name (assuming unique).
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
            aliases = cls.get_phrase_aliases()
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

class Autocompleter(object):
    """
    Autocompleter class
    """
    def __init__(self, name=settings.DEFAULT_NAME):
        self.name = name
        self.auto_base_name = 'djac.%s'
        self.prefix_base_name = self.auto_base_name + '.p.%s'
        self.prefix_set_base_name =  self.auto_base_name + '.ps'
        self.exact_base_name = self.auto_base_name + '.e.%s'
        self.exact_set_base_name = self.auto_base_name + '.es'
        
        # Make connection with Redis
        self.redis = redis.Redis(host=settings.REDIS_CONNECTION['host'], 
            port=settings.REDIS_CONNECTION['port'], 
            db=settings.REDIS_CONNECTION['db'])

    def store(self, obj):
        """
        Add an object to the autocompleter
        """
        provider = self._get_provider(obj)
        if provider == None:
            return
        provider_name = provider.get_provider_name()

        # Get data from provider
        obj_id = provider.get_obj_id()
        norm_terms = provider.get_norm_terms()
        score = provider.get_score() 
        data = provider.get_data()
        
        # Turn each normalized term into possible prefixes
        phrases = []
        
        for norm_term in norm_terms:
            phrases = phrases + \
                utils.get_autocompleter_phrases_for_term(norm_term, settings.MAX_NUM_WORDS)

        # Start pipeline
        pipe = self.redis.pipeline()

        # Processes prefixes of object, placing object ID in sorted sets
        for phrase in phrases:
            phrase_prefix = ''
            for char in phrase:
                phrase_prefix += char
                # Store prefix to obj ID mapping, with score
                key = self.prefix_base_name % (provider_name, phrase_prefix,)
                pipe.zadd(key, obj_id, score)

                # Store autocompleter to prefix mapping so we know all prefixes
                # of an autocompleter
                key =  self.prefix_set_base_name % (provider_name,)
                pipe.sadd(key, phrase_prefix)

        # Process normalized term of object, placing object ID in a sorted set 
        # representing exact matches
        for norm_term in norm_terms:
            # Store exact term to obj ID mapping, with score
            key = self.exact_base_name % (provider_name, norm_term,)
            pipe.zadd(key, obj_id, score)

            # Store autocompleter to exact term mapping so we know all exact terms
            # of an autocompleter
            key = self.exact_set_base_name % (provider_name,)
            pipe.sadd(key, norm_term)

        # Store obj ID to data mapping
        key = self.auto_base_name % (provider_name,)
        pipe.hset(key, obj_id, self._serialize_data(data))

        # End pipeline
        pipe.execute()

    def store_all(self):
        """
        Store all objects of all providers register with this autocompleter.
        """
        provider_classes = registry.get_all(self.name)
        if provider_classes == None:
            return

        for provider_class in provider_classes:
            for obj in provider_class.get_queryset().iterator():
                self.store(obj)

    def remove(self, obj):
        """
        Remove an object from the autocompleter
        """
        provider = self._get_provider(obj)
        if provider == None:
            return
        provider_name = provider.get_provider_name()

        # Get data from provider
        obj_id = provider.get_obj_id()
        norm_terms = provider.get_norm_terms()

        # Turn each normalized term into possible prefixes
        phrases = []
        norm_terms = provider.get_norm_terms()
        for norm_term in norm_terms:
            phrases = phrases + \
                utils.get_autocompleter_phrases_for_term(norm_term, settings.MAX_NUM_WORDS) 

        # Start pipeline
        pipe = self.redis.pipeline()

        # Processes prefixes of object, removing object ID from sorted sets
        for phrase in phrases:
            phrase_prefix = ''
            for char in phrase:
                phrase_prefix += char
                key = self.prefix_base_name % (provider_name, phrase_prefix,)
                pipe.zrem(key, obj_id)
                
                key =  self.prefix_set_base_name % (provider_name,)
                pipe.srem(key, phrase_prefix)

        # Process normalized terms of object, removing object ID from a sorted set 
        # representing exact matches
        for norm_term in norm_terms:
            key = self.exact_base_name % (provider_name, norm_term,)
            pipe.zrem(key, obj_id)

            key = self.exact_set_base_name % (provider_name,)
            pipe.srem(key, norm_term)

        # Remove model ID to data mapping
        key = self.auto_base_name % (provider_name,)
        pipe.hdel(key, obj_id)

        # End pipeline
        pipe.execute()

    def remove_all(self):
        """
        Remove all objects for a given autocompleter.
        This will clear the autocompleter even when the underlying objects don't exist.
        """
        providers = self._get_all_providers()
        if providers == None:
            return

        for provider in providers:
            provider_name = provider.provider_name

            # Get list of all prefixes for autocompleter
            prefix_set_name = self.prefix_set_base_name % (provider_name,)
            prefixes = self.redis.smembers(prefix_set_name)

            # Get list of all exact match terms for autocompleter
            exact_set_name = self.exact_set_base_name % (provider_name,)
            norm_terms = self.redis.smembers(exact_set_name)

            # Start pipeline
            pipe = self.redis.pipeline()

            # For each prefix, delete sorted set
            for prefix in prefixes:
                key = self.prefix_base_name % (provider_name, prefix,)
                pipe.delete(key)
            # Delete the set of prefixes
            pipe.delete(prefix_set_name)

            # For each exact match term, deleting sorted set
            for norm_term in norm_terms:
                key = self.exact_base_name % (provider_name, norm_term,)
                pipe.delete(key)
            # Delete the set of exact matches
            pipe.delete(exact_set_name)

            # Remove the entire obj ID to data mapping hash
            key = self.auto_base_name % (provider_name,)
            pipe.delete(key)

            # End pipeline
            pipe.execute()

    def suggest(self, term):
        """
        Suggest matching objects, given a term
        """
        providers = self._get_all_providers()
        if providers == None:
            return []

        num_providers = len(providers)
        provider_results = SortedDict()
        norm_term = utils.get_normalized_term(term)
        norm_words = norm_term.split()
        num_words = len(norm_words)

        # Get the matched result IDs
        pipe = self.redis.pipeline()
        for provider in providers:
            provider_name = provider.provider_name

            # Get base autocompleter matches
            key = self.prefix_base_name % (provider_name, norm_term,)
            pipe.zrevrange(key, 0, settings.MAX_RESULTS - 1)

            # Get exact matches
            if settings.MOVE_EXACT_MATCHES_TO_TOP:
                key = self.exact_base_name % (provider_name, norm_term,)
                pipe.zrevrange(key, 0, settings.MAX_RESULTS - 1)

            # Get out of order matches
            if settings.MATCH_OUT_OF_ORDER and num_words > 1:
                keys = [self.prefix_base_name % (provider_name, i,) for i in norm_words]
                pipe.zinterstore("oooresults", keys, aggregate='MIN')
                pipe.zrevrange("oooresults", 0, settings.MAX_RESULTS - 1)
        results = [i for i in pipe.execute() if type(i) == list]

        # Now combine the 3 different kind of ID into one unifed
        # result ID list per provider
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

        # Get the results for each provider
        pipe = self.redis.pipeline()
        for provider_name, ids in provider_results.items():
            if len(ids) > 0:
                key = self.auto_base_name % (provider_name,)
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

    def _serialize_data(self, data_dict):
        return simplejson.dumps(data_dict)

    def _deserialize_data(self, raw):
        return simplejson.loads(raw)


















    
    def exact_suggest(self, term):
        """
        Suggest matching objects exacting matching term given, given a term
        """
        norm_term = utils.get_normalized_term(term)
        exact_auto_term = '%s.%s' % (self.exact_base_name, norm_term,)
        exact_ids = self.redis.zrevrange(exact_auto_term, 0, settings.MAX_RESULTS - 1)
        if len(exact_ids) == 0:
            return []
        
        # Get match data based on our ID list
        results = self.redis.hmget(self.auto_base_name, exact_ids)
        # We shouldn't have any bogus matches, but if we do clear out before we deserialize
        results = [i for i in results if i != None]
        results = [self._deserialize_data(i) for i in results]
        return results
    
    def _get_provider(self, obj):
        provider_class = registry.get(self.name, type(obj))
        if provider_class == None:
            return None
        return provider_class(obj)

    def _get_all_providers(self):
        return registry.get_all(self.name)


