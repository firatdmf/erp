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
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from accounting.models import Book
from authentication.client_tokens import client_from
from erp.storefront import answers_in_storefront_language

ITEM_LIMIT = 200


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
        warehouse = item.product.warehouse
        place = warehouse.shown_as
        places[place] = places.get(place, 0) + available
        if not by_variant:
            items.append({
                "id": item.pk,
                "available": float(available),
                "lot": item.lot_number or "",
                "location": place,
            })
    return JsonResponse({
        "sku": sku,
        "tracking": "variant" if by_variant else "item",
        # The code ("m", "piece"), not a label: the storefront words it in
        # the shopper's own language.
        "unit": product.unit if product else "",
        "locations": [{"location": place, "available": float(total)}
                      for place, total in places.items()],
        "items": items,
    })
