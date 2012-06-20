from django.http import HttpResponse, HttpResponseServerError
from django.utils import simplejson

from autocompleter import settings
from autocompleter import Autocompleter


def suggest(request, name=settings.DEFAULT_NAME):
    if settings.SUGGEST_PARAMETER_NAME in request.GET:
        term = request.GET[settings.SUGGEST_PARAMETER_NAME]
        ac = Autocompleter(name)
        results = ac.suggest(term)

        json = simplejson.dumps(results)
        return HttpResponse(json, mimetype='application/json')
    return HttpResponseServerError("Search paramater not found.")


def exact_suggest(request, name=settings.DEFAULT_NAME):
    if settings.SUGGEST_PARAMETER_NAME in request.GET:
        term = request.GET[settings.SUGGEST_PARAMETER_NAME]
        ac = Autocompleter(name)
        results = ac.exact_suggest(term)

        json = simplejson.dumps(results)
        return HttpResponse(json, mimetype='application/json')
    return HttpResponseServerError("Search paramater not found.")
