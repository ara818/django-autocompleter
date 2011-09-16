from django.conf.urls.defaults import *

urlpatterns = patterns('autocompleter.views',
    url(r'^suggest$', 'suggest', name='suggest'),
    url(r'^suggest/(?P<name>[0-9A-Za-z_-]+)$', 'suggest', name='suggest_named'),
    url(r'^exact_suggest$', 'suggest', name='exact_suggest'),
    url(r'^exact_suggest/(?P<name>[0-9A-Za-z_-]+)$', 'exact_suggest', name='exact_suggest_named'),
)