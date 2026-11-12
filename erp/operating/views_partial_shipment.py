"""The "Ship part of the order" page — see operating.partial_shipment."""
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from .models import Order
from .partial_shipment import (
    PartialShipError, group_packs, open_halves, order_lines, refusal, split_off,
)


def _allowed(request, halves):
    """Splitting writes to every half's order, so — like completing a split
    order — it takes someone who holds every book it is in. Sales reps
    don't ship."""
    from accounting.services_accounts import member_can_use_book
    from erp.roles import is_sales_rep
    from .split_orders import order_book
    if is_sales_rep(request.user):
        return False
    member = getattr(request.user, "member", None)
    return all(order_book(h) is None or member_can_use_book(member, order_book(h))
               for h in halves)


@login_required
def order_ship_part(request, pk):
    from .split_orders import combined_number

    order = get_object_or_404(Order.objects.select_related("current_account__book"), pk=pk)
    halves = open_halves(order)
    if not _allowed(request, halves):
        raise Http404("No such record.")
    reason = refusal(order)
    if reason:
        messages.error(request, reason)
        return redirect("operating:order_detail", pk=order.pk)

    if request.method == "POST":
        ticked = [int(x) for x in request.POST.getlist("pack") if x.isdigit()]
        quantities = {}
        for key, value in request.POST.items():
            if key.startswith("ship_") and key[5:].isdigit() and value.strip() != "":
                quantities[int(key[5:])] = value
        moving = [int(x) for x in request.POST.getlist("move_adjustment") if x.isdigit()]
        try:
            follow_ups = split_off(order, ticked, quantities, moving, user=request.user)
        except PartialShipError as exc:
            messages.error(request, str(exc))
            return redirect("operating:order_ship_part", pk=order.pk)
        kept = Order.objects.get(pk=order.pk)
        if kept in follow_ups:
            # This half waits with the rest; the page to complete is the
            # one that ships.
            kept = kept.continued_from
        messages.success(request, _(
            "The rest continues on %(numbers)s. Complete this order when its packages leave."
        ) % {"numbers": combined_number(follow_ups)})
        return redirect("operating:order_detail", pk=kept.pk)

    packs = group_packs(order, halves)
    rows = order_lines(halves)
    # What each package holds, to name it on the page.
    contents = {p.pk: [] for p in packs}
    for row in rows:
        row.rolls_json = json.dumps([[p, str(q)] for p, q in row.rolls])
        sku = row.item.product_variant.variant_sku if row.item.product_variant_id else ""
        for pack_id, qty in row.rolls:
            if pack_id in contents:
                contents[pack_id].append((sku, qty))
        if not row.rolls and row.pack_id in contents:
            contents[row.pack_id].append((sku, row.ordered))
    pack_rows = []
    for p in packs:
        held = contents[p.pk]
        pack_rows.append({
            "pack": p,
            "rolls": len(held),
            "amount": sum((q for _s, q in held), Decimal("0")),
            "skus": sorted({s for s, _q in held if s}),
        })
    adjustments = [a for h in halves for a in h.adjustments.all()]
    return render(request, "operating/order_ship_part.html", {
        "order": order,
        "number": combined_number(halves),
        "split": len(halves) > 1,
        "pack_rows": pack_rows,
        "rows": rows,
        "adjustments": adjustments,
    })
