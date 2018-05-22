import json

from django.http import HttpResponse, HttpResponseServerError
from django.views.generic import View

from autocompleter import settings
from autocompleter import Autocompleter


class SuggestView(View):
    def get(self, request, name):
        if settings.SUGGEST_PARAMETER_NAME in request.GET:
            term = request.GET[settings.SUGGEST_PARAMETER_NAME]
            ac = Autocompleter(name)
            if settings.FACET_PARAMETER_NAME in request.GET:
                facets = request.GET[settings.FACET_PARAMETER_NAME]
                facets = json.loads(facets)
                results = ac.suggest(term, facets=facets)
            else:
                results = ac.suggest(term)

            json_response = json.dumps(results)
            return HttpResponse(json_response, content_type='application/json')
        return HttpResponseServerError("Search parameter not found.")


class ExactSuggestView(View):
    def get(self, request, name):
        if settings.SUGGEST_PARAMETER_NAME in request.GET:
            term = request.GET[settings.SUGGEST_PARAMETER_NAME]
            ac = Autocompleter(name)
            results = ac.exact_suggest(term)

            json_response = json.dumps(results)
            return HttpResponse(json_response, content_type='application/json')
        return HttpResponseServerError("Search parameter not found.")
