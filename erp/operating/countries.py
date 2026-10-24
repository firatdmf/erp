"""Countries as the storefront stores them: ISO 3166-1 alpha-2 codes.

A code never changes, and it is what carriers' rate tables and customs
duty tables key on, so web addresses and orders hold "TR", not "Turkey"
in one place and "Türkiye" in another. Names are for people only, in
the reader's language. A value saved before codes is shown as it is.
"""
import gettext
from functools import lru_cache

import pycountry
from django.utils.translation import get_language


@lru_cache(maxsize=None)
def _translate(language):
    try:
        return gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=[language]).gettext
    except OSError:
        return lambda name: name


def _language():
    return (get_language() or "en").split("-")[0]


def country_name(value):
    """The name of the country `value` codes for; anything else as it is."""
    value = (value or "").strip()
    country = pycountry.countries.get(alpha_2=value.upper()) if len(value) == 2 else None
    if country is None:
        return value
    return _translate(_language())(country.name)


def country_choices():
    """(code, name) for every country, sorted by name in the reader's language."""
    translate = _translate(_language())
    return sorted(((c.alpha_2, translate(c.name)) for c in pycountry.countries),
                  key=lambda choice: choice[1].casefold())
