import json

from django.http import HttpResponse, HttpResponseServerError

from autocompleter import settings
from autocompleter import Autocompleter


def suggest(request, name):
    if settings.SUGGEST_PARAMETER_NAME in request.GET:
        term = request.GET[settings.SUGGEST_PARAMETER_NAME]
        ac = Autocompleter(name)
        results = ac.suggest(term)

        json_response = json.dumps(results)
        return HttpResponse(json_response, mimetype='application/json')
    return HttpResponseServerError("Search parameter not found.")


def exact_suggest(request, name):
    if settings.SUGGEST_PARAMETER_NAME in request.GET:
        term = request.GET[settings.SUGGEST_PARAMETER_NAME]
        ac = Autocompleter(name)
        results = ac.exact_suggest(term)

        json_response = json.dumps(results)
        return HttpResponse(json_response, mimetype='application/json')
    return HttpResponseServerError("Search parameter not found.")
