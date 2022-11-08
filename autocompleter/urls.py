from django.urls import re_path
from autocompleter.views import ExactSuggestView, SuggestView

urlpatterns = [
    re_path(
        r"^suggest/(?P<name>[0-9A-Za-z_-]+)$", SuggestView.as_view(), name="suggest"
    ),
    re_path(
        r"^exact_suggest/(?P<name>[0-9A-Za-z_-]+)$",
        ExactSuggestView.as_view(),
        name="exact_suggest",
    ),
]
