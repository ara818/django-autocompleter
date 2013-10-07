from django.conf.urls import *

urlpatterns = patterns('autocompleter.views',
    url(r'^suggest/(?P<name>[0-9A-Za-z_-]+)$', 'suggest', name='suggest'),
    url(r'^exact_suggest/(?P<name>[0-9A-Za-z_-]+)$', 'exact_suggest', name='exact_suggest'),
)
