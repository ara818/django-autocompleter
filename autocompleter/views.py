from django.http import Http404, HttpResponse

from django.utils import simplejson

from autocompleter import settings
from autocompleter import Autocompleter

def suggest(request, name=settings.DEFAULT_NAME):
    if settings.SUGGEST_PARAMETER_NAME in request.GET:
        term = request.GET[settings.SUGGEST_PARAMETER_NAME]
        ac = Autocompleter(name)
        results = ac.suggest(term)

        json = simplejson.dumps(results)
        return HttpResponse(json)
    return HttpResponse("fuck")
        