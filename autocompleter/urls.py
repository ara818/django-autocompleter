from django.conf.urls import *
from autocompleter.views import ExactSuggestView, SuggestView

urlpatterns = [
    url(r'^suggest/(?P<name>[0-9A-Za-z_-]+)$', SuggestView.as_view(), name='suggest'),
    url(r'^exact_suggest/(?P<name>[0-9A-Za-z_-]+)$', ExactSuggestView.as_view(), name='exact_suggest'),
]
