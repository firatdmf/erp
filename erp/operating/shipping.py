"""Which warehouses may send goods to a buyer's country, and in what order
to offer them (the storefront's roll picker, and the web order after it).

A warehouse always ships inside its own country. To another country it
ships unless that country's ShippingRule says otherwise: nothing from
abroad, or not from these countries. Of the warehouse countries that may,
the buyer's own comes first, then those the rule says ship there best,
then the rest, nearest first.

A warehouse with no country typed in can't be judged, so no rule stops
it; nor can a buyer whose country isn't known — everything is offered
and the web order checks again against the delivery address.
"""
from math import asin, cos, radians, sin, sqrt

from .country_points import POINTS


def code(value):
    """`value` as a country code ("TR"), or "" when it isn't one."""
    value = (value or "").strip().upper()
    return value if len(value) == 2 and value.isalpha() else ""


def rules():
    """{destination code: ShippingRule}."""
    from .models import ShippingRule
    return {rule.destination: rule for rule in ShippingRule.objects.all()}


def can_ship(origin, destination, known=None):
    """Whether a warehouse in `origin` may send to `destination`."""
    origin, destination = code(origin), code(destination)
    if not origin or not destination or origin == destination:
        return True
    rule = (rules() if known is None else known).get(destination)
    if rule is None:
        return True
    return not rule.only_from_inside and origin not in rule.not_from


def distance_km(a, b):
    """Kilometres between the middles of two countries, or None."""
    pa, pb = POINTS.get(code(a)), POINTS.get(code(b))
    if pa is None or pb is None:
        return None
    lat1, lon1, lat2, lon2 = map(radians, (*pa, *pb))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return round(2 * 6371 * asin(sqrt(h)))


def preference(origin, destination, known=None):
    """A sort key: lower is offered first. Own country, then "ships best
    from", then nearest; unknown places last among equals."""
    origin, destination = code(origin), code(destination)
    if not destination:
        return (0, 0)
    if origin == destination:
        return (0, 0)
    rule = (rules() if known is None else known).get(destination)
    if rule is not None and origin in rule.best_from:
        return (1, rule.best_from.index(origin))
    km = distance_km(origin, destination)
    return (2, km if km is not None else 10 ** 6)


def buyer_country(client, typed=""):
    """Where a signed-in customer's goods go: their default address's
    country when it is a code, else the one the storefront sent (the
    country of their connection), else ""."""
    if client is not None:
        address = client.addresses.order_by("-is_default", "-created_at").first()
        if address is not None and code(address.country):
            return code(address.country)
    return code(typed)
