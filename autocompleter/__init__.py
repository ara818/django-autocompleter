import redis

from django.utils import simplejson as json

from autocompleter import settings
from autocompleter import utils

_providers = {}
def register(model_class, provider):
    """
    Register a model with a autocomplete provider.
    A model can have a list of providers that it uses for autocomplete.
    """
    _providers[model_class] = (provider)

def unregister(model_class, provider):
    """
    Urnegister a model with a autocomplete provider.
    """
    if model_class in _providers:
        del(_providers[model_class])


class AutocompleterProvider(object):
    def __init__(self, obj):
        self.obj = obj

    def get_id(self):
        """
        The id for the object, should be unique for each model.
        """
        raise NotImplementedError
    
    def get_model_id(self):
        """
        Create a cross-model unique ID. Will normally not have to override this.
        """
        base_id = self.get_id()
        return "%s.%s" % (self.obj.__class__.__name__.lower(), base_id,)

    def get_term(self):
        """
        The term for the object, which will support autocompletion.
        """
        raise NotImplementedError
    
    def get_terms(self):
        """
        Optional. Define this is an object can be searched for using more than one term.
        """
        return [self.get_term()]
    
    def get_norm_terms(self):
        """
        Normalize each term in list of terms. Will normally not have to override this.
        """
        return [utils.get_normalized_term(term) for term in self.get_terms()]

    def get_score(self):
        """
        The score for the object, that will dictate the order of autocompletion.
        """
        return 0

    def get_data(self):
        """
        Any data you want to send along with object.
        """
        return {}
    
    def get_object_as_dict(self):
        d = {}
        d['id'] = self.get_model_id()
        d['terms'] = self.get_terms()
        d['norm_terms'] = self.get_norm_terms()
        d['score'] = self.get_score()
        d['data'] = self.get_data()
        return d

class Autocompleter(object):
    """
    Autocompleter class
    """
    def __init__(self, name):
        self.name = name
        self.full_name = 'autocompleter.%s' % (name,)
        
        # Make connection with Redis
        self.redis = redis.Redis(host=settings.REDIS_CONNECTION['host'], 
            port=settings.REDIS_CONNECTION['port'], 
            db=settings.REDIS_CONNECTION['db'])

    def store(self, obj):
        provider = self._get_provider(obj)

        # Get data from provider
        obj_dict = provider.get_object_as_dict()
        model_id = obj_dict['id']
        score = obj_dict['score']
        terms = obj_dict['terms']
        norm_terms = obj_dict['norm_terms']
        
        # Turn each term into possible prefixes
        prefixes = []
        for norm_term in norm_terms:
            prefixes = prefixes + utils.get_prefixes_for_term(norm_term)

        # Add all prefixes of object to sorted set; 
        for prefix in prefixes:
            partial_prefix = ''
            for char in prefix:
                partial_prefix += char
                key = '%s.%s' % (self.full_name, partial_prefix,)
                self.redis.zadd(key, model_id, score)

        # Store ID to data mapping
        self.redis.hset(self.full_name, model_id, self._serialize_data(obj_dict))

    def remove(self, obj):
        pass
    
    def suggest(self, term):
        norm_term = utils.get_normalized_term(term)
        full_term = '%s.%s' % (self.full_name, norm_term)
        ids = self.redis.zrevrange(full_term, 0, settings.MAX_RESULTS - 1)
        results = self.redis.hmget(self.full_name, ids)
        results = [self._deserialize_data(i) for i in results]
    
        # If we're told to move exact matches to top, do another pass on the 
        # results and move any items whose results 
        if settings.MOVE_EXACT_MATCHES_TO_TOP:
            new_results = []
            for result in results:
                if norm_term in result['norm_terms']:
                    new_results.insert(0, result)
                else:
                    new_results.append(result)
            return new_results
        else:
            return results
            
    
    def _get_provider(self, obj):
        try:
            provider_class = _providers[type(obj)]
            return provider_class(obj)
        except KeyError:
            raise TypeError("Don't know what do with %s" % obj.__name__)
    
    def _serialize_data(self, data_dict):
        return json.dumps(data_dict)

    def _deserialize_data(self, raw):
        return json.loads(raw) 