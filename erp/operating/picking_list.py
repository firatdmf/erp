"""The picking list: which rolls the warehouse pulls for an order.

The order print counts rolls without naming them (it goes to the customer),
and the packing list names them only once they are in a package. Between
the two, the rolls reserved for an order were written down nowhere — so
this sheet lists them: under the warehouse they stand in, beneath the line
they fill, each by barcode and lot, with how much of the roll to take and
whether that is the whole roll or a cut. Lines the rolls do not yet cover
close the sheet, so it never reads as complete when it is not.

It is for the warehouse floor and prints no prices and no customer name —
only the customer's id. A split order prints every half, one shipment on
one sheet, as the order's page shows it.
"""
from decimal import Decimal
from types import SimpleNamespace

from django.urls import reverse
from django.shortcuts import get_object_or_404

from .models import Order


def customer_id_label(order):
    """"Contact #388" — which customer, without saying who. Contacts,
    companies and web clients are numbered separately, so the kind is part
    of the id."""
    from django.utils.translation import gettext as _
    if order.contact_id:
        return _("Contact #%(id)s") % {"id": order.contact_id}
    if order.company_id:
        return _("Company #%(id)s") % {"id": order.company_id}
    if order.web_client_id:
        return _("Web client #%(id)s") % {"id": order.web_client_id}
    return ""


def build_picking_groups(order):
    """One order's rolls, under the warehouse each stands in and the line
    it fills. Returns (warehouses, short):

      warehouses — [{name, lines: [{item, rolls, metres}], roll_count, metres}]
                   by warehouse name; a line whose rolls stand in two
                   warehouses appears under each with that warehouse's rolls
      short      — [{item, needed, picked, missing}], the lines the
                   reserved rolls do not make up, in the order's line order

    A roll shipped already (its reservation consumed) has had the
    reservation's metres taken off it, so they are added back: the sheet
    says what the roll held when it was picked.
    """
    from .views import build_order_print_rows

    items, _total, _qty, _packs = build_order_print_rows(order)
    items.sort(key=lambda i: ((getattr(i.product, "title", "") or "").casefold(),
                              (getattr(i.product_variant, "variant_sku", "") or ""), i.pk))
    order_of = {it.pk: n for n, it in enumerate(items)}
    by_pk = {it.pk: it for it in items}

    warehouses, picked = {}, {}
    for r in (order.stock_reservations
              .select_related("stock_item__product__warehouse", "warehouse_product")
              .order_by("stock_item__barcode", "pk")):
        roll = r.stock_item
        wh = roll.product.warehouse
        take = r.quantity or Decimal("0")
        on_roll = (roll.quantity_remaining or Decimal("0")) + (take if r.consumed else 0)
        shelf = warehouses.setdefault(wh.pk if wh else None, SimpleNamespace(
            name=getattr(wh, "name", "") or "", lines={}, roll_count=0, metres=Decimal("0")))
        item = by_pk.get(r.order_item_id)
        line = shelf.lines.setdefault(r.order_item_id if item else ("loose", r.warehouse_product_id),
                                      SimpleNamespace(item=item, product=r.warehouse_product,
                                                      rolls=[], metres=Decimal("0")))
        line.rolls.append(SimpleNamespace(
            barcode=roll.barcode or f"#{roll.pk}", lot=roll.lot_number or "",
            on_roll=on_roll, take=take, whole=take >= on_roll))
        line.metres += take
        line.summary = line_summary(line)
        shelf.roll_count += 1
        shelf.metres += take
        if item:
            picked[item.pk] = picked.get(item.pk, Decimal("0")) + take

    out = []
    for shelf in sorted(warehouses.values(), key=lambda s: s.name.casefold()):
        # Lines as the order lists them; rolls tied to no line after them.
        shelf.lines = sorted(shelf.lines.values(),
                             key=lambda l: (l.item is None, order_of.get(getattr(l.item, "pk", None), 0)))
        shelf.products = by_product(shelf.lines)
        out.append(shelf)

    short = []
    for it in items:
        needed = it.quantity or Decimal("0")
        got = picked.get(it.pk, Decimal("0"))
        if got < needed:
            short.append(SimpleNamespace(item=it, needed=needed, picked=got, missing=needed - got))
    return out, by_product(short)


def by_product(lines):
    """Lines of one parent product under a single heading, so its
    variants read as K12447 → .G50, .G93 rather than the parent repeated
    on every line. `lines` come sorted by product already, so a run of
    the same product is consecutive. A line tied to no order line (a
    roll reserved loose) stands alone.

    Each group is {item, product, lines, single}: `single` when the group
    is one line with no variant — the heading then says everything, and
    the line gets no row of its own."""
    groups = []
    for line in lines:
        item = line.item
        key = ("item", item.product_id) if item else ("loose", id(line))
        if groups and groups[-1].key == key:
            groups[-1].lines.append(line)
            continue
        groups.append(SimpleNamespace(key=key, item=item, product=getattr(line, "product", None),
                                      lines=[line]))
    for g in groups:
        g.single = len(g.lines) == 1 and not (g.item and g.item.product_variant_id)
    return groups


def line_summary(line):
    """"60.40 of 60.40 m" — what a line's rolls come to against what it
    ordered; on the heading or the variant row, whichever the line has."""
    from django.utils.translation import gettext as _
    if line.item is None:
        return _("Not tied to a line")
    return _("%(metres)s of %(needed)s %(unit)s") % {
        "metres": f"{line.metres:,.2f}",
        "needed": f"{line.item.quantity or 0:,.2f}",
        "unit": line.item.unit_short}


def tint(color, strength=0.12):
    """The brand colour faded toward white — the ground a variant SKU is
    printed on in that colour. Worked out here rather than in CSS: the
    colour is the house's setting, and the PDF renderer is not a browser
    to be trusted with color-mix(). Anything that is not #rrggbb gets a
    neutral ground."""
    h = (color or "").lstrip("#")
    if len(h) != 6:
        return "#F3F4F6"
    try:
        rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return "#F3F4F6"
    return "#" + "".join(f"{round(255 - (255 - c) * strength):02X}" for c in rgb)


def order_picking_list(request, pk):
    from accounting.services_accounts import brand_name_for
    from erp.nejum_credit import brand_color
    from erp.pdf_render import document_response
    from .split_orders import split_halves, combined_number, order_book
    import segno

    order = get_object_or_404(Order, pk=pk)
    halves = split_halves(order)
    groups, roll_count, metres, units = [], 0, Decimal("0"), set()
    for half in halves:
        warehouses, short = build_picking_groups(half)
        groups.append({"order": half, "book": getattr(order_book(half), "name", ""),
                       "warehouses": warehouses, "short": short})
        for shelf in warehouses:
            roll_count += shelf.roll_count
            metres += shelf.metres
            for line in shelf.lines:
                units.add(line.item.unit_short if line.item else line.product.unit_short)

    # A link, not a payload: a phone camera opens it, and whoever may see
    # the order lands on it.
    order_url = request.build_absolute_uri(reverse("operating:order_detail", args=[order.pk]))
    color = brand_color()
    qr = segno.make(order_url, error="m").svg_data_uri(scale=3, border=0, dark="#0F1419")

    return document_response(request, "operating/order_picking_list.html", {
        "order": order,
        "groups": groups,
        "split": len(halves) > 1,
        "number": combined_number(halves),
        "customer_id": customer_id_label(order),
        "carrier": order.get_carrier_display() if order.carrier else "",
        "roll_count": roll_count,
        "total_metres": metres,
        # One unit or none: "metres" across rolls and pieces is no total.
        "total_unit": units.pop() if len(units) == 1 else None,
        "qr": qr,
        "brand_line": brand_name_for(),
        "brand_color": color,
        "brand_tint": tint(color),
    }, f"picking_{order.order_number or order.pk}.pdf")
