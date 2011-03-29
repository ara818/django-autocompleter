from django.conf.urls.defaults import *

urlpatterns = patterns('autocompleter.views',
    url(r'^suggest$', 'suggest', name='suggest'),
    url(r'^suggest/(?P<name>[0-9A-Za-z_-]+)$', 'suggest', name='suggest_named'),
)