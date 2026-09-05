from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template
from django.utils.formats import number_format
from django.utils.translation import gettext as _

register = template.Library()


# Canonical unit code → translatable label. Lets us store any of
# {"adet", "pcs", "piece"} in the DB but render based on the active
# locale. Unknown codes pass through untouched.
_UNIT_CANONICAL = {
    "adet": "pcs",
    "pcs":  "pcs",
    "piece": "pcs",
    "pieces": "pcs",
    "metre": "m",
    "metres": "m",
    "meter": "m",
    "meters": "m",
    "m": "m",
    "kilogram": "kg",
    "kilograms": "kg",
    "kilo": "kg",
    "kg": "kg",
    "g": "g",
    "gram": "g",
    "grams": "g",
    "lt": "L",
    "litre": "L",
    "litres": "L",
    "liter": "L",
    "liters": "L",
    "l": "L",
}


@register.filter(name="unit_loc")
def unit_loc(value):
    """Render a unit code in the active locale. `adet` ↔ `pcs`, etc."""
    if not value:
        return ""
    key = str(value).strip().lower()
    canonical = _UNIT_CANONICAL.get(key, value)
    return _(canonical)


@register.filter(name="dictlookup")
def dictlookup(d, key):
    """Look up a key in a dict-like object from a template."""
    if d is None:
        return ""
    try:
        return d.get(key, "")
    except AttributeError:
        try:
            return d[key]
        except (KeyError, TypeError, IndexError):
            return ""


@register.filter(name="absval")
def absval(value):
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value


@register.filter(name="signed")
def signed(value):
    """Format a number with explicit sign: +42.00 / -42.00 / 0.00"""
    try:
        v = float(value or 0)
        if v > 0:
            return f"+{v:,.2f}"
        return f"{v:,.2f}"
    except (TypeError, ValueError):
        return value


@register.simple_tag(name="conversion_facts")
def conversion_facts_tag(obj):
    """What `obj` converted at, or None when it is already in base currency.

    Thin wrapper so a template can say
    `{% conversion_facts payment as fx %}{% if fx %}…{% endif %}` — see
    accounting.services_accounts.conversion_facts for the rules.
    """
    from accounting.services_accounts import conversion_facts
    return conversion_facts(obj)


@register.filter(name="money")
def money(value, decimals=2):
    """Group a money amount the way the *active locale* groups numbers.

    The old `floatformat:2|intcomma` pipeline is right in English and
    wrong in Turkish: floatformat localises first, so intcomma is handed
    the string "1234567,50", cannot read it as a number, and falls back
    to its English-only regex — printing "1,234,567,50" where Turkish
    wants "1.234.567,50". number_format does the grouping and the
    decimal separator together, in one locale-aware pass.
    """
    if value is None or value == "":
        return value
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    decimals = int(decimals)
    # number_format truncates the tail; floatformat, which this filter
    # replaces, rounds it. Quantise first so the digits do not change.
    amount = amount.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return number_format(amount, decimal_pos=decimals, force_grouping=True)
