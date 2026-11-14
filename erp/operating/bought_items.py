"""What a client has bought, one row per variant, with what they paid.

The CRM page answers "have I sold this to them before, and at what
price?" without opening order after order. Read off the order lines;
cancelled and returned orders are left out, as nothing was charged for
them in the end.
"""
from collections import OrderedDict
from decimal import Decimal

from marketing.units import unit_short

from .models import OrderItem
from .split_orders import half_number


LEFT_OUT = ("cancelled", "returned")


def bought_items(orders):
    """`orders`: the client's orders, already narrowed to the books the
    viewer can see. Returns one dict per variant, last bought first:
    product, variant, unit, sales (every line, newest first), last (the
    newest of them), order_count and quantity (the summed amount)."""
    lines = (
        OrderItem.objects
        .filter(order__in=orders.exclude(order_status__in=LEFT_OUT))
        .select_related("order__currency", "product", "product_variant")
        .order_by("-order__order_date", "-order__created_at", "-pk")
    )
    rows = OrderedDict()
    for line in lines:
        order = line.order
        row = rows.get(line.product_variant_id)
        if row is None:
            row = rows[line.product_variant_id] = {
                "product": line.product,
                "variant": line.product_variant,
                "unit": unit_short(line.product.unit),
                "sales": [],
                "order_pks": set(),
                "quantity": Decimal("0"),
            }
        row["sales"].append({
            "order_pk": order.pk,
            "number": half_number(order),
            "date": order.order_date or order.created_at.date(),
            "symbol": order.currency_symbol,
            "price": line.price,
            "quantity": line.quantity,
        })
        row["order_pks"].add(order.pk)
        row["quantity"] += line.quantity or 0
    result = []
    for row in rows.values():
        row["last"] = row["sales"][0]
        row["order_count"] = len(row.pop("order_pks"))
        result.append(row)
    return result


def items_with_variant():
    """The Prefetch for an order list whose rows open onto their lines:
    each line with its product and variant, in the order they were added."""
    from django.db.models import Prefetch
    return Prefetch("items", queryset=OrderItem.objects
                    .select_related("product", "product_variant").order_by("pk"))


def attach_lines(rows):
    """Give each row of operating.split_orders.order_rows its lines, as
    row_lines, each with unit_short and symbol (its own half's currency).

    An ordinary row reads its prefetched items (items_with_variant); a
    split row lists every half's lines but a half's cancelled on its own,
    as its total does — fetched here, in one query."""
    groups = {o.split_group for o in rows if len(o.row_numbers) > 1}
    split_lines = {}
    if groups:
        for line in (OrderItem.objects
                     .filter(order__split_group__in=groups)
                     .select_related("order__currency", "product", "product_variant")
                     .order_by("order_id", "pk")):
            split_lines.setdefault(line.order.split_group, []).append(line)
    for o in rows:
        if len(o.row_numbers) > 1:
            lines = split_lines.get(o.split_group, [])
            o.row_lines = [l for l in lines if l.order.order_status != "cancelled"] or lines
        else:
            o.row_lines = list(o.items.all())
            for line in o.row_lines:
                line.order = o  # its currency, without a query per line
        for line in o.row_lines:
            line.unit_short = unit_short(line.product.unit)
            line.symbol = line.order.currency_symbol
    return rows
