"""What a signed-in business customer may pick from stock, for the
storefront's product page.

A variant tracked item by item (marketing.units.by_variant is False) is
offered roll by roll: each free roll with its length, its lot — so a
buyer can keep one job in one dye lot — and where it stands. One tracked
by variant has no roll to choose, so it is offered as a quantity per
place instead.

Only warehouses switched on for the storefront (Warehouse.on_storefront)
are offered: goods a buyer can't be sent are not theirs to pick. Read
from the same list the order form's roll picker reads
(views.free_stock_items), so a customer is never shown a roll staff
could not sell. Left out on purpose: cost, barcodes, books and the
warehouse's street address. A roll goes by its id, which is what the
order will send back.
"""
from decimal import Decimal

from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from accounting.models import Book
from authentication.client_tokens import client_from
from erp.storefront import answers_in_storefront_language

ITEM_LIMIT = 200


def place_of(warehouse):
    """Where a warehouse's stock stands, as the storefront is told: the
    city as typed and the country as its code ("TR"), which the storefront
    names in the shopper's language; `location` is the two together, or
    the warehouse's name when neither is filled in."""
    return {"location": warehouse.shown_as, "city": warehouse.city.strip(),
            "country": warehouse.country}


def offered(sku):
    """{stock item id: (item, free quantity)} of everything of `sku` the
    storefront offers right now — the list stock_items shows, unlimited."""
    from .views import free_stock_items
    return {item.pk: (item, available)
            for item, available in free_stock_items(sku, Book.objects.all(), on_storefront=True)}


def tracked_by_item(sku):
    """Whether `sku` is a variant whose stock items each carry a label of
    their own — the only kind a customer can pick roll by roll."""
    from marketing.models import ProductVariant
    variant = (ProductVariant.objects.select_related("product")
               .filter(variant_sku__iexact=sku).first())
    return variant is not None and not variant.product.sold_by_count


@answers_in_storefront_language
@require_GET
def stock_items(request):
    """GET ?sku=<variant SKU>, with the customer's Bearer token."""
    from .views import free_stock_items

    if client_from(request) is None:
        return JsonResponse({"error": _("Sign in to see the stock.")}, status=401)
    sku = (request.GET.get("sku") or "").strip()
    if not sku:
        return JsonResponse({"error": _("The product is missing.")}, status=400)

    free = free_stock_items(sku, Book.objects.all(), limit=ITEM_LIMIT, on_storefront=True)
    product = free[0][0].product if free else None
    by_variant = bool(product and product.sold_by_count)

    places = {}
    items = []
    for item, available in free:
        place = place_of(item.product.warehouse)
        total = places.setdefault(place["location"], {**place, "available": 0})
        total["available"] += available
        if not by_variant:
            items.append({
                "id": item.pk,
                "available": float(available),
                "lot": item.lot_number or "",
                **place,
            })
    return JsonResponse({
        "sku": sku,
        "tracking": "variant" if by_variant else "item",
        # The code ("m", "piece"), not a label: the storefront words it in
        # the shopper's own language.
        "unit": product.unit if product else "",
        "locations": [{**place, "available": float(place["available"])}
                      for place in places.values()],
        "items": items,
    })


class RollsGone(Exception):
    """Picked rolls the storefront no longer offers as they were picked —
    sold, cut, or on a warehouse switched off. `ids` names them."""

    def __init__(self, ids):
        super().__init__(ids)
        self.ids = ids


def _ids(values):
    """Stock item ids from what a cart or an order sent — ids or
    {"id": …} records — each once, in the order given."""
    out = []
    for value in values or []:
        raw = value.get("id") if isinstance(value, dict) else value
        try:
            pk = int(raw)
        except (TypeError, ValueError):
            continue
        if pk not in out:
            out.append(pk)
    return out


class BadCut(ValueError):
    """A length that can't be cut: not a whole number of the roll's unit,
    and not the whole roll either. `ids` names the rolls."""

    def __init__(self, ids):
        super().__init__(ids)
        self.ids = ids


def _requests(values):
    """{stock item id: the length asked for, or None for the whole roll},
    in the order given; a roll named twice keeps the later length."""
    from decimal import Decimal, InvalidOperation
    out = {}
    for value in values or []:
        raw = value.get("id") if isinstance(value, dict) else value
        try:
            pk = int(raw)
        except (TypeError, ValueError):
            continue
        quantity = value.get("quantity") if isinstance(value, dict) else None
        try:
            quantity = None if quantity in (None, "") else Decimal(str(quantity))
        except InvalidOperation:
            quantity = Decimal("-1")
        out.pop(pk, None)
        out[pk] = quantity
    return out


def can_cut(quantity, available):
    """Whether `quantity` can be taken off a roll with `available` free:
    the whole roll, whatever it measures, or a whole number of its unit —
    12 m, never 12.5 m — that the roll holds."""
    if quantity is None or quantity <= 0 or quantity > available:
        return False
    return quantity == available or quantity == quantity.to_integral_value()


def pick(sku, values):
    """The cart's record of picked rolls of `sku`: [{"id", "quantity"}] —
    the length to cut from each, or the whole roll where none is given.
    Raises RollsGone for rolls the storefront no longer offers, or that no
    longer hold what is asked of them, and BadCut for a length that can't
    be cut (see can_cut)."""
    from decimal import Decimal
    asked = _requests(values)
    free = offered(sku)
    gone = [pk for pk, quantity in asked.items()
            if pk not in free or (quantity is not None and quantity > free[pk][1])]
    if gone:
        raise RollsGone(gone)
    picks = []
    bad = []
    for pk, quantity in asked.items():
        available = free[pk][1]
        quantity = available if quantity is None else quantity
        if not can_cut(quantity, available):
            bad.append(pk)
        picks.append({"id": pk, "quantity": str(quantity.quantize(Decimal("0.01")))})
    if bad:
        raise BadCut(bad)
    return picks


def picked_total(picks):
    from decimal import Decimal
    return sum((Decimal(str(p["quantity"])) for p in picks), Decimal("0"))


def gone_from(sku, picks):
    """The ids of `picks` that no longer have what they held when picked."""
    from decimal import Decimal
    free = offered(sku)
    return [p["id"] for p in picks
            if p["id"] not in free or free[p["id"]][1] < Decimal(str(p["quantity"]))]


def describe(sku, picks):
    """Picked rolls as the cart shows them: each with its lot and place,
    what it held when picked, and whether it still does."""
    from decimal import Decimal
    from .models import WarehouseProductItem
    free = offered(sku)
    known = {item.pk: item for item in WarehouseProductItem.objects
             .select_related("product__warehouse").filter(pk__in=[p["id"] for p in picks])}
    out = []
    for p in picks:
        item = known.get(p["id"])
        quantity = Decimal(str(p["quantity"]))
        out.append({
            "id": p["id"],
            "quantity": float(quantity),
            "lot": (item.lot_number or "") if item else "",
            **(place_of(item.product.warehouse) if item and item.product_id
               else {"location": "", "city": "", "country": ""}),
            "still_free": p["id"] in free and free[p["id"]][1] >= quantity,
            # What the roll holds free now, so the cart can offer the rest
            # of it, or say it is a whole roll.
            "on_roll": float(free[p["id"]][1]) if p["id"] in free else 0.0,
            # The code ("m", "kg"); the storefront words it.
            "unit": item.product.unit if item and item.product_id else "",
        })
    return out
