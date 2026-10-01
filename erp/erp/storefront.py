"""The public website's endpoints answer in the website's language.

The ERP follows each member's own language setting, but a call from the
storefront carries no member and no setting: left alone it would be
answered in LANGUAGE_CODE, and a shopper on the Turkish site would read
English errors. These endpoints are answered in STOREFRONT_LANGUAGE.
"""
from functools import wraps

from django.conf import settings
from django.utils import translation


def answers_in_storefront_language(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        language = getattr(settings, "STOREFRONT_LANGUAGE", "tr")
        with translation.override(language):
            return view(request, *args, **kwargs)
    return wrapped
