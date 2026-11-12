"""Ship part of an order; the rest continues on a follow-up order.

Goods leave in packages, and sometimes only some of them are ready: a
customer's first sacks go today, the rest next week. An order ships once —
its sale, its stock cut and its frozen billed quantities all happen at that
one moment (post_order_movement, apply_order_status_change) — so a partial
shipment is two orders, not one order shipped twice:

  * the order keeps what is in the packages ticked to go now, and is
    completed as any order is;
  * everything else moves to a follow-up order — its own number, same
    customer, account and prices, still open — that points back at it
    (Order.continued_from).

What moves:
  * a line's goods outside the ticked packages: the whole line when none of
    it ships, otherwise a new line on the follow-up for the rest, with the
    rolls that are not going;
  * the packages not ticked, with what is in them;
  * purchases still on their way in: their goods have not arrived, so they
    cannot be in this shipment;
  * the extra lines (OrderAdjustment) the person chose to move. The rest
    stay on the order that ships.

An order split across books is still one order: every half splits at once,
and the follow-ups are one follow-up split across the same books. A half
none of whose goods ship becomes a follow-up itself rather than shipping
empty.
"""
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.utils.translation import gettext as _

from .models import Order, OrderAdjustment, OrderItem, OrderStockReservation, Pack

ZERO = Decimal("0")


class PartialShipError(Exception):
    """Why the split was refused; the message is for the person."""


@dataclass
class LineRow:
    item: OrderItem
    half: Order
    ordered: Decimal
    # (pack id or None, meters) for each roll still held for the line.
    rolls: list = field(default_factory=list)
    # The package a line with no rolls was packed into, if any.
    pack_id: int = None
    # A purchase still on its way in owns the line: none of it can ship.
    locked: bool = False
    ships: Decimal = ZERO

    def rolls_in(self, ticked):
        return sum((q for p, q in self.rolls if p in ticked), ZERO)

    def rolls_out(self, ticked):
        return sum((q for p, q in self.rolls if p not in ticked), ZERO)

    def suggested(self, ticked):
        """What the line ships when the person changes nothing."""
        if self.locked:
            return ZERO
        if self.rolls:
            going, staying = self.rolls_in(ticked), self.rolls_out(ticked)
            # Every roll goes: the line is done, as a full shipment would
            # bill it — the ordered quantity, not just what was scanned.
            if going and not staying:
                return self.ordered
            return min(going, self.ordered)
        return self.ordered if self.pack_id in ticked else ZERO

    def bounds(self, ticked):
        """(least, most) the line may ship: at least the rolls going, and
        no more than leaves room for the rolls staying."""
        if self.locked:
            return ZERO, ZERO
        if self.rolls:
            return (min(self.rolls_in(ticked), self.ordered),
                    max(self.ordered - self.rolls_out(ticked), ZERO))
        return ZERO, self.ordered


def open_halves(order):
    """The order's halves still in play, first made first — just [order]
    when it is not split. A half cancelled on its own takes no part."""
    if not order.split_group:
        return [order]
    return list(Order.objects.filter(split_group=order.split_group)
                .exclude(order_status="cancelled")
                .select_related("current_account__book", "currency")
                .order_by("pk"))


def refusal(order):
    """Why this order cannot ship in part, or None."""
    from .order_purchases import order_is_open
    if order.is_retail_order:
        return _("A retail order goes out at the counter in one piece.")
    if not order_is_open(order):
        return _("Only an open order can ship in part.")
    return None


def order_lines(halves):
    """A LineRow for every line of every half."""
    from .order_purchases import purchase_locked_lines
    rows = []
    for half in halves:
        locked = purchase_locked_lines(half)
        items = (half.items.select_related("product_variant", "product", "packed_assignment")
                 .order_by("pk"))
        holds = {}
        for r in (OrderStockReservation.objects
                  .filter(order_item__order=half, consumed=False)
                  .only("order_item_id", "pack_id", "quantity")):
            holds.setdefault(r.order_item_id, []).append((r.pack_id, r.quantity or ZERO))
        for item in items:
            assignment = getattr(item, "packed_assignment", None)
            rows.append(LineRow(
                item=item, half=half, ordered=item.quantity or ZERO,
                rolls=holds.get(item.pk, []),
                pack_id=item.pack_id or (assignment.pack_id if assignment else None),
                locked=item.pk in locked,
            ))
    return rows


def group_packs(order, halves):
    from .split_orders import order_packs
    ids = {h.pk for h in halves}
    return [p for p in order_packs(order) if p.order_id in ids]


def _parse(value):
    from decimal import InvalidOperation
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _line_name(item):
    return item.product_variant.variant_sku if item.product_variant_id else f"#{item.pk}"


def _number(order):
    return order.order_number or f"#{order.pk}"


# Copied from the order onto its follow-up: everything but these — what
# belongs to a shipment that happened, a payment taken, or a document
# issued for the order that ships.
_NOT_CARRIED = (
    "qr_code_url", "payment_id", "paid_amount", "paid_currency",
    "original_price", "card_type", "card_association", "card_last_four",
    "tracking_number", "shipped_at", "delivered_at", "ettn", "invoice_date",
    "stock_consumed_at", "billed_line_quantities", "billed_quantities_frozen_at",
)


def _follow_up(half, user):
    """A new open order for the rest of `half`: same customer, account,
    currency and addresses, a number of its own, no lines yet.

    Inserted without Order.save()'s signals: they would tell the customer
    and the staff about a new order, and this is the same order going on.
    The change log says what happened instead (split_off)."""
    from django.utils import timezone
    from .models import OrderNumberSequence

    f = Order.objects.get(pk=half.pk)
    f.pk = f.id = None
    f._state.adding = True
    for name in _NOT_CARRIED:
        setattr(f, name, None)
    f.order_number = OrderNumberSequence.take()
    f.split_group = None
    f.continued_from = half
    if user is not None and getattr(user, "is_authenticated", False):
        f.created_by = user
    now = timezone.now()
    f.created_at = f.updated_at = now
    Order.objects.bulk_create([f])
    return f


def _move_pack(pack, target):
    """Put `pack` on `target`, keeping its number unless target already
    has one by it (old split orders numbered each half from 1)."""
    from django.db.models import Max
    number = pack.pack_number
    if Pack.objects.filter(order=target, pack_number=number).exclude(pk=pack.pk).exists():
        top = Pack.objects.filter(order=target).aggregate(m=Max("pack_number"))["m"] or 0
        number = top + 1
    Pack.objects.filter(pk=pack.pk).update(order=target, pack_number=number)


def split_off(order, ticked_pack_ids, quantities=None, moving_adjustments=(), user=None):
    """Keep on `order` (and its halves) what ships now; move the rest to a
    follow-up order. Returns the follow-up orders, first made first.

    ticked_pack_ids — the packages going now.
    quantities — {line pk: what it ships}; a line left out ships its
                 suggested quantity (LineRow.suggested).
    moving_adjustments — pks of extra lines that go to the follow-up.

    Raises PartialShipError, leaving everything as it was."""
    from .audit import log_change
    from .order_purchases import syncing

    quantities = quantities or {}
    with transaction.atomic(), syncing():
        order = Order.objects.select_for_update().get(pk=order.pk)
        halves = open_halves(order)
        list(Order.objects.select_for_update().filter(pk__in=[h.pk for h in halves]))
        for half in halves:
            reason = refusal(half)
            if reason:
                raise PartialShipError(reason)

        packs = group_packs(order, halves)
        ticked = {p.pk for p in packs} & {int(x) for x in ticked_pack_ids}
        rows = order_lines(halves)
        for row in rows:
            raw = quantities.get(row.item.pk)
            q = row.suggested(ticked) if raw is None else _parse(raw)
            if q is None or q < 0:
                raise PartialShipError(_("%(sku)s: the quantity to ship is not a number.")
                                       % {"sku": _line_name(row.item)})
            least, most = row.bounds(ticked)
            if row.locked and q:
                raise PartialShipError(
                    _("%(sku)s comes from a purchase that hasn't been received — none of it can ship yet.")
                    % {"sku": _line_name(row.item)})
            if q < least:
                raise PartialShipError(
                    _("%(sku)s: the ticked packages hold %(qty)s of it, so at least that ships.")
                    % {"sku": _line_name(row.item), "qty": least})
            if q > most:
                raise PartialShipError(
                    _("%(sku)s: at most %(qty)s can ship — its other rolls stay behind.")
                    % {"sku": _line_name(row.item), "qty": most})
            row.ships = q

        if not any(r.ships for r in rows):
            raise PartialShipError(_("Nothing would ship. Tick the packages going now."))
        if all(r.ships >= r.ordered for r in rows):
            raise PartialShipError(_("Everything ships — complete the order as usual."))

        moving = set(OrderAdjustment.objects
                     .filter(order__in=halves, pk__in=[int(x) for x in moving_adjustments])
                     .values_list("pk", flat=True))

        shipping, follow_ups, whole = [], [], []
        for half in halves:
            mine = [r for r in rows if r.half.pk == half.pk]
            ships = any(r.ships for r in mine)
            rest = any(r.ships < r.ordered for r in mine)
            adj = half.adjustments.filter(pk__in=moving)
            if not ships:
                # Nothing of this half goes: it waits as it is, as part of
                # the follow-up, rather than shipping empty.
                whole.append(half)
                follow_ups.append(half)
                continue
            shipping.append(half)
            if not rest and not adj.exists():
                continue
            f = _follow_up(half, user)
            follow_ups.append(f)
            for r in mine:
                left = r.ordered - r.ships
                if left <= 0:
                    continue
                item = r.item
                if not r.ships:
                    OrderItem.objects.filter(pk=item.pk).update(order=f)
                    OrderStockReservation.objects.filter(
                        order_item=item, consumed=False).update(order=f)
                    log_change(half, "item_removed", item_label=_line_name(item),
                               old=item.quantity, new=_("moved to %(n)s") % {"n": _number(f)})
                    continue
                going_rolls = r.rolls_in(ticked)
                out = item.outsourced_quantity
                ship_out = rest_out = None
                if out is not None:
                    ship_out = min(out, max(r.ships - going_rolls, ZERO))
                    rest_out = out - ship_out
                new = OrderItem.objects.get(pk=item.pk)
                new.pk = new.id = None
                new._state.adding = True
                new.order = f
                new.pack = None
                new.quantity = left
                new.outsourced_quantity = rest_out
                new.save()
                OrderItem.objects.filter(pk=item.pk).update(
                    quantity=r.ships, outsourced_quantity=ship_out)
                (OrderStockReservation.objects
                 .filter(order_item=item, consumed=False)
                 .exclude(pack_id__in=ticked)
                 .update(order=f, order_item=new))
                log_change(half, "item_updated", item_label=_line_name(item),
                           old=item.quantity,
                           new=_("%(q)s ships; %(left)s moved to %(n)s")
                               % {"q": r.ships, "left": left, "n": _number(f)})
            for a in adj:
                OrderAdjustment.objects.filter(pk=a.pk).update(order=f)
                log_change(half, "field", field="adjustments", old=f"{a.label} {a.amount}",
                           new=_("moved to %(n)s") % {"n": _number(f)})
            # Goods still on their way in cannot be in this shipment.
            moved = list(half.supplier_purchases.filter(status="ordered"))
            if moved:
                half.supplier_purchases.filter(pk__in=[p.pk for p in moved]).update(for_order=f)
                log_change(half, "field", field="purchase",
                           new=_("%(numbers)s now bought for %(n)s")
                               % {"numbers": ", ".join(p.number for p in moved), "n": _number(f)})

        # Rolls held for the order but for no line go with their package.
        for half in shipping:
            f = next((x for x in follow_ups if x.continued_from_id == half.pk), None)
            if f is not None:
                (OrderStockReservation.objects
                 .filter(order=half, order_item__isnull=True, consumed=False)
                 .exclude(pack_id__in=ticked).update(order=f))

        # The packages: each goes with its side, onto the first made order
        # there (where split_orders.pack_holder looks for them).
        lead_ship = min(shipping, key=lambda o: o.pk)
        lead_follow = min(follow_ups, key=lambda o: o.pk)
        ship_ids = {o.pk for o in shipping}
        follow_ids = {o.pk for o in follow_ups}
        for p in packs:
            if p.pk in ticked and p.order_id not in ship_ids:
                _move_pack(p, lead_ship)
            elif p.pk not in ticked and p.order_id not in follow_ids:
                _move_pack(p, lead_follow)

        # Each side is one order on screen: split across books when it has
        # more than one, plain otherwise.
        Order.objects.filter(pk__in=ship_ids).update(
            split_group=order.split_group if len(shipping) > 1 else None)
        Order.objects.filter(pk__in=follow_ids).update(
            split_group=uuid.uuid4() if len(follow_ups) > 1 else None)
        if whole:
            Order.objects.filter(pk__in=[h.pk for h in whole]).update(continued_from=lead_ship)

        names = ", ".join(_number(f) for f in sorted(follow_ups, key=lambda o: o.pk))
        for half in shipping:
            log_change(half, "field", field="continued", new=_("Shipped in part; the rest continues on %(n)s") % {"n": names})
        for f in follow_ups:
            log_change(f, "created" if f not in whole else "field", field="continued_from",
                       new=_("The rest of %(n)s after part of it shipped")
                           % {"n": ", ".join(_number(h) for h in shipping)})
        # Fresh copies: the ones in hand predate the updates above, and a
        # save from them would put the old split group back.
        for o in Order.objects.filter(pk__in=ship_ids | follow_ids):
            o.update_status_from_items()

        return sorted(follow_ups, key=lambda o: o.pk)
