from django import template
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
