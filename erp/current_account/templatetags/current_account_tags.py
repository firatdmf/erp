from django import template

register = template.Library()


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
