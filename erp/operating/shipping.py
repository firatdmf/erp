"""Shipping reach: which warehouses may send goods to a buyer's country,
and in what order to offer them (the storefront's roll picker, and the
web order after it).

Each warehouse says where its goods may go (Warehouse.ships_to): every
country, only those listed, or every one but those listed. It always
ships inside its own country. Of the warehouses that may, the buyer's own
country's come first, then those that ship there best
(Warehouse.ships_best_to), then the rest, nearest first.

A buyer whose country isn't known is offered everything; the web order
checks again against the delivery address.
"""
from math import asin, cos, radians, sin, sqrt

from .country_points import POINTS


def code(value):
    """`value` as a country code ("TR"), or "" when it isn't one."""
    value = (value or "").strip().upper()
    return value if len(value) == 2 and value.isalpha() else ""


def can_ship(warehouse, destination):
    """Whether `warehouse` may send to `destination`."""
    destination = code(destination)
    if not destination or destination == code(warehouse.country):
        return True
    if warehouse.ships_to == "only":
        return destination in warehouse.ships_to_countries
    if warehouse.ships_to == "except":
        return destination not in warehouse.ships_to_countries
    return True


def distance_km(a, b):
    """Kilometres between the middles of two countries, or None."""
    pa, pb = POINTS.get(code(a)), POINTS.get(code(b))
    if pa is None or pb is None:
        return None
    lat1, lon1, lat2, lon2 = map(radians, (*pa, *pb))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return round(2 * 6371 * asin(sqrt(h)))


def preference(warehouse, destination):
    """A sort key: lower is offered first. Own country, then "ships best
    to", then nearest; a warehouse with no country last among equals."""
    destination = code(destination)
    if not destination or code(warehouse.country) == destination:
        return (0, 0)
    if destination in warehouse.ships_best_to:
        return (1, 0)
    km = distance_km(warehouse.country, destination)
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
