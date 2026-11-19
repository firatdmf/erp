"""Our own rolls sent out to a supplier to be worked on, on a purchase.

See models_processing for the idea. The purchase form posts the rolls
going out in its plan as

    "goods_out": [{"barcode": "TLS05014728"}, ...]

and what comes back as its ordinary products ("goods in"). The rest
follows the purchase's own life:

  save (draft)   save_draft_lines()   the out rolls are marked away
  confirm        perform_intake() receives the goods in, with
                 start_receipt()      the out rolls it may meet by barcode,
                 return_roll()        each one that came back, and
                 settle()             the rest used up, the cost spread
  undo receipt   unreceive_lines()    each out roll back as it was, away
  cancel         release_lines() /    a draft's rolls come home; a
                 unreceive_lines()    received one's go back first

Every book works the same way: the out rolls must be on the shelves of the
purchase's own book.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

ZERO = Decimal("0")


class ProcessingError(Exception):
    """Goods out that can't be saved or received, with a message for the
    person at the form. Nothing has been written."""


def plan_rows(plan):
    """The goods-out rows of a purchase plan, as posted."""
    rows = (plan or {}).get("goods_out") or []
    return [r for r in rows if isinstance(r, dict)
            and (str(r.get("barcode") or "").strip() or str(r.get("stock_item_id") or "").strip())]


def _left(roll):
    left = roll.quantity_remaining if roll.quantity_remaining is not None else roll.quantity
    return Decimal(left or 0)


def _free(roll):
    """What of `roll` no order holds — all of it may go only when this is
    all of it."""
    from operating.views import _roll_available_meters
    return _roll_available_meters(roll)


def _find_roll(row, *, book=None, skip=()):
    """(item, by_printed) for a goods-out row: the item its id, barcode or
    "#id" names — or, for goods counted in pieces, the oldest box of the
    product whose printed barcode it is that has some free (`book`'s
    shelves, leaving out the ids in `skip`). by_printed says it was found
    the second way: the code named the product, not one box of it."""
    from operating.models import WarehouseProductItem

    qs = WarehouseProductItem.objects.select_related(
        "product", "product__warehouse", "product__catalog_variant__product",
        "processing_line__invoice")
    stock_id = str(row.get("stock_item_id") or "").strip()
    if stock_id.isdigit():
        return qs.filter(pk=int(stock_id)).first(), False
    code = str(row.get("barcode") or "").strip()
    if not code:
        return None, False
    item = WarehouseProductItem.matching_pick_key(qs, code).first()
    if item is None and book is not None:
        from operating.views import _batches_by_printed_barcode
        for batch in _batches_by_printed_barcode(code, [book]):
            if batch.pk not in skip and _free(batch) > 0:
                return qs.get(pk=batch.pk), True
    return item, False


def _roll_name(roll):
    if roll.barcode:
        return roll.barcode
    if roll.lot_number:
        return f"{roll.product.item_noun} {roll.lot_number}"
    return f"#{roll.pk}"


def _qty(value):
    return format(Decimal(value).normalize(), "f")


def _unit(roll):
    variant = roll.product.catalog_variant
    return ((variant.product.unit if variant is not None else None) or "m")[:20]


def variant_label(variant):
    """"N1464T · ecru" — the SKU, and its values when they say more."""
    if variant is None:
        return ""
    values = [v.product_variant_attribute_value for v in
              variant.product_variant_attribute_values.all()
              if (v.product_variant_attribute_value or "").strip()]
    return " · ".join([variant.variant_sku or variant.product.title, *values[:3]])


def send_problem(roll, *, book, invoice=None, count=None):
    """Why `roll` can't go out to be worked on, as a sentence naming it, or
    None: used up, on another book's shelves, held for an order, or already
    away on another purchase (`invoice` is the one being saved). `count`:
    only so many of it go (goods counted in pieces) — then it is enough
    that no order holds those."""
    name = _roll_name(roll)
    if roll.status == "consumed" or _left(roll) <= 0:
        return _("%(code)s is used up — there is nothing left of it to send.") % {"code": name}
    warehouse = roll.product.warehouse
    if book is not None and warehouse.accounting_book_id != book.pk:
        return (_("%(code)s is on the shelves of %(book)s — send it on a purchase "
                  "of that book.") % {"code": name, "book": warehouse.accounting_book})
    line = roll.processing_line
    if line is not None and (invoice is None or line.invoice_id != invoice.pk):
        return (_("%(code)s is already away on purchase %(number)s.")
                % {"code": name, "number": line.invoice.display_number})
    if count is not None:
        if count > _left(roll):
            return (_("%(code)s holds %(left)s — there aren't %(count)s of it to send.")
                    % {"code": name, "left": _qty(_left(roll)), "count": _qty(count)})
        if roll.barcode and count < _left(roll):
            return (_("%(code)s goes out whole — it has a barcode of its own.")
                    % {"code": name})
        if line is None and count > _free(roll):
            return (_("Only %(free)s of %(code)s are free to send — orders hold the rest.")
                    % {"code": name, "free": _qty(_free(roll))})
        if count < _left(roll):
            return None
    holds = list(roll.reservations.filter(consumed=False).select_related("order"))
    if holds:
        orders = sorted({str(h.order.order_number or h.order_id) for h in holds})
        return (_("%(code)s is reserved for order %(orders)s — take it off the order "
                  "before sending it.") % {"code": name, "orders": ", ".join(orders)})
    return None


def _own_split(invoice, roll):
    """How many this purchase has already split off `roll` to send."""
    if invoice is None or invoice.pk is None:
        return ZERO
    return sum((Decimal(l.quantity) for l in invoice.processing_lines.filter(
        split_from=roll, received_at__isnull=True)), ZERO)


def lookup(code, *, book, invoice=None, skip=()):
    """An item as the purchase form shows it in goods out: what it is, how
    much is on it, where, and why it can't go, if it can't. A box of goods
    counted in pieces is `counted`: the form asks how many of it go
    (`free` at most). None when nothing has `code`."""
    roll, by_printed = _find_roll({"barcode": code}, book=book, skip=skip)
    if roll is None:
        return None
    wp = roll.product
    variant = wp.catalog_variant
    counted = not roll.barcode
    own = _own_split(invoice, roll) if counted else ZERO
    free = (_free(roll) if roll.processing_line_id is None else _left(roll)) + own
    return {
        "stock_item_id": roll.pk,
        "barcode": roll.pick_key,
        "printed": (code if by_printed else (wp.printed_barcode if counted else "")),
        "counted": counted,
        "name": _roll_name(roll),
        "sku": (variant.variant_sku if variant is not None else None) or wp.sku or "",
        "label": variant_label(variant) if variant is not None else wp.name,
        "quantity": _qty(_left(roll) + own),
        "free": _qty(free),
        "unit": _unit(roll),
        "warehouse": wp.warehouse.name,
        "problem": (send_problem(roll, book=book, invoice=invoice, count=ZERO + 1)
                    if counted and free > 0 else
                    send_problem(roll, book=book, invoice=invoice)),
    }


def _wanted(plan, *, book):
    """[(item, count)] the plan sends: count is how many of it, None for
    all of it. A row found by a product's printed barcode is one piece,
    as a scan of it is. Raises ProcessingError for a row that names
    nothing, a count that isn't one, or an item named twice."""
    from decimal import InvalidOperation

    out, seen = [], set()
    for row in plan_rows(plan):
        roll, by_printed = _find_roll(row, book=book, skip=seen)
        if roll is None:
            code = str(row.get("barcode") or row.get("stock_item_id") or "?").strip()
            raise ProcessingError(_("Nothing in stock has the barcode %(code)s.") % {"code": code})
        if roll.pk in seen:
            raise ProcessingError(_("%(code)s is on this purchase twice.")
                                  % {"code": _roll_name(roll)})
        seen.add(roll.pk)
        raw = str(row.get("quantity") or "").strip()
        if raw:
            try:
                count = Decimal(raw)
            except InvalidOperation:
                count = None
            if count is None or not count.is_finite() or count <= 0:
                raise ProcessingError(_("How many of %(code)s go out? Enter a number above 0, "
                                        "not “%(qty)s”.") % {"code": _roll_name(roll), "qty": raw})
        else:
            count = Decimal(1) if by_printed else None
        out.append((roll, count))
    return out


def _split(box, count, *, invoice, user=None):
    """`count` of `box` taken out into an item of their own, to go out for
    work: the box holds that many fewer. Value moves with them and nothing
    is posted — it is still the same stock."""
    from operating.models import StockMovement, WarehouseProductItem

    piece = WarehouseProductItem.objects.create(
        product=box.product, quantity=count, quantity_remaining=count, status="in_stock",
        lot_number=box.lot_number, supplier_barcode=box.supplier_barcode,
        is_second=box.is_second, unit_cost_base=box.unit_cost_base,
        purchase_invoice_item=box.purchase_invoice_item, scanned_by=user)
    box.quantity = Decimal(box.quantity or 0) - count
    box.quantity_remaining = _left(box) - count
    box.save(update_fields=["quantity", "quantity_remaining"])
    reason = f"{invoice.display_number}: {_qty(count)} taken out of {_roll_name(box)} for work"
    StockMovement.objects.create(product=box.product, stock_item=box, movement_type="adjustment",
                                 quantity=-count, reason=reason, created_by=user)
    StockMovement.objects.create(product=box.product, stock_item=piece, movement_type="adjustment",
                                 quantity=count, reason=reason, created_by=user)
    return piece


def _put_back(line, *, user=None):
    """A split-off part home unworked: back into the box it came out of,
    which may have been emptied since. The part is left used up."""
    from operating.models import StockMovement, WarehouseProductItem

    piece = WarehouseProductItem.objects.select_for_update(of=("self",)).filter(
        pk=line.stock_item_id).first()
    box = WarehouseProductItem.objects.select_for_update(of=("self",)).filter(
        pk=line.split_from_id).first()
    if piece is None or box is None or piece.status == "consumed":
        return
    count = _left(piece)
    box.quantity = Decimal(box.quantity or 0) + count
    box.quantity_remaining = _left(box) + count
    box.status = "in_stock" if box.quantity_remaining >= box.quantity else "partial"
    box.save(update_fields=["quantity", "quantity_remaining", "status"])
    piece.quantity_remaining = ZERO
    piece.status = "consumed"
    piece.processing_line = None
    piece.save(update_fields=["quantity_remaining", "status", "processing_line"])
    reason = f"{line.invoice.display_number}: {_qty(count)} back into {_roll_name(box)}"
    StockMovement.objects.create(product=piece.product, stock_item=piece, movement_type="adjustment",
                                 quantity=-count, reason=reason, created_by=user)
    StockMovement.objects.create(product=box.product, stock_item=box, movement_type="adjustment",
                                 quantity=count, reason=reason, created_by=user)


def _bring_home(line, *, user=None):
    from operating.models import WarehouseProductItem

    if line.split_from_id:
        _put_back(line, user=user)
    else:
        WarehouseProductItem.objects.filter(pk=line.stock_item_id, processing_line=line) \
            .update(processing_line=None)


@transaction.atomic
def save_draft_lines(invoice, plan, *, user=None):
    """Make the draft's goods out what its plan says: items taken off it
    come home, new ones go away, a part of a box is split off it. Raises
    ProcessingError, the caller rolling the save back."""
    from operating.models import WarehouseProductItem
    from .models_processing import ProcessingLine

    wanted = _wanted(plan, book=invoice.book)
    lines = list(invoice.processing_lines.select_for_update(of=("self",))
                 .filter(received_at__isnull=True))
    list(WarehouseProductItem.objects.select_for_update(of=("self",)).filter(
        pk__in={r.pk for r, _n in wanted} | {l.stock_item_id for l in lines if l.stock_item_id}
        | {l.split_from_id for l in lines if l.split_from_id}))

    want = {roll.pk: count for roll, count in wanted}
    kept = {}
    for line in lines:
        origin = line.split_from_id or line.stock_item_id
        if origin in want and origin not in kept:
            count = want[origin]
            if (count == line.quantity if line.split_from_id
                    else count is None or count == line.quantity):
                kept[origin] = line
                continue
        _bring_home(line, user=user)
        line.delete()

    sent = []
    for roll, count in wanted:
        if roll.pk in kept:
            sent.append(kept[roll.pk].stock_item)
            continue
        roll.refresh_from_db()
        whole = count is None or count == _left(roll)
        problem = send_problem(roll, book=invoice.book, invoice=invoice,
                               count=None if whole else count)
        if problem:
            raise ProcessingError(problem)
        line = ProcessingLine(invoice=invoice, unit=_unit(roll))
        if whole:
            line.stock_item, line.quantity = roll, _left(roll)
        else:
            line.stock_item = _split(roll, count, invoice=invoice, user=user)
            line.split_from, line.quantity = roll, count
        line.barcode = _roll_name(roll)
        line.save()
        WarehouseProductItem.objects.filter(pk=line.stock_item_id).update(processing_line=line)
        sent.append(line.stock_item)
    return sent


@transaction.atomic
def release_lines(invoice, *, user=None):
    """A draft cancelled: its out items are back on the shelf as they were,
    a part split off a box back in it."""
    lines = list(invoice.processing_lines.select_related("invoice")
                 .filter(received_at__isnull=True))
    for line in lines:
        _bring_home(line, user=user)
    return lines


# ── Receiving ────────────────────────────────────────────────────────────

class Receipt:
    """One receipt's goods out, from start_receipt() to settle(): the out
    rolls by barcode, as they stood before, and which of them came back."""

    def __init__(self, invoice, lines, rolls):
        self.invoice = invoice
        self.lines = lines                    # {roll id: ProcessingLine}
        self.by_code = {(r.barcode or "").upper(): r for r in rolls.values() if r.barcode}
        self.returned = {}                    # roll id → meters back
        self.came_in = []                     # ids of every roll goods in brought

    def roll_for(self, code):
        """The out roll a goods-in barcode names, or None."""
        return self.by_code.get((code or "").strip().upper())

    def ids_by_code(self):
        return {r.pk: r.barcode for r in self.by_code.values()}


def start_receipt(invoice):
    """Lock the purchase's out rolls and note how each stood. None when it
    sends nothing out. Must run inside the caller's transaction."""
    from operating.models import WarehouseProductItem
    from .services_posting import stock_unit_cost

    lines = {l.stock_item_id: l for l in
             invoice.processing_lines.select_for_update(of=("self",))
             .filter(received_at__isnull=True)}
    if not lines:
        return None
    rolls = {r.pk: r for r in WarehouseProductItem.objects.select_for_update(of=("self",))
             .select_related("product", "product__warehouse", "purchase_invoice_item")
             .filter(pk__in=[k for k in lines if k])}
    for roll_id, line in lines.items():
        roll = rolls.get(roll_id)
        if roll is None or roll.processing_line_id != line.pk:
            raise ProcessingError(_("%(code)s is no longer away on this purchase.")
                                  % {"code": line.barcode or "?"})
        line.from_product = roll.product
        line.unit_cost_before = stock_unit_cost(roll)
        if line.unit_cost_before is None:
            raise ProcessingError(_("%(code)s has no cost, so what it adds to the goods "
                                    "that came back can't be worked out.") % {"code": line.barcode})
        line.length_before = roll.quantity
        line.status_before = roll.status
        line.quantity = _left(roll)
    return Receipt(invoice, lines, rolls)


def return_roll(receipt, roll, wp, quantity, *, user=None, unit_cost=None):
    """An out roll is back, as goods in: it moves onto `wp` (the variant it
    came back as) and holds `quantity` now. Its cost is settled later.
    What it lost or gained in the work is an adjustment, not a correction:
    its value is carried over by settle(), not written off."""
    from operating.models import StockMovement
    from operating.views_warehouse import _move_roll

    if roll.product_id != wp.pk:
        _move_roll(roll, wp, user=user,
                   reason_out=f"{receipt.invoice.display_number}: worked on — now {wp.sku}",
                   reason_in=f"{receipt.invoice.display_number}: worked on — was "
                             f"{receipt.lines[roll.pk].from_product.sku}")
    before = _left(roll)
    if quantity != before:
        StockMovement.objects.create(
            product=wp, stock_item=roll, movement_type="adjustment",
            quantity=quantity - before,
            reason=f"{receipt.invoice.display_number}: came back {quantity} from {before}",
            reference=roll.barcode, created_by=user)
    gone = Decimal(roll.quantity or 0) - before        # cut before it went out
    roll.quantity = gone + quantity
    roll.quantity_remaining = quantity
    roll.status = "in_stock" if gone <= 0 else "partial"
    roll.processing_line = None
    roll.unit_cost_base = unit_cost if unit_cost is not None else wp.cost_usd
    roll.save(update_fields=["product", "quantity", "quantity_remaining", "status",
                             "processing_line", "unit_cost_base"])
    receipt.returned[roll.pk] = quantity
    receipt.came_in.append(roll.pk)


def settle(receipt, *, user=None):
    """After goods in: every out roll that did not come back was used up in
    the work; the value of everything that went out is spread per unit over
    everything that came in, on top of what each costs. Returns the
    warehouse rows touched, to recount."""
    from operating.models import StockMovement, WarehouseProductItem

    pool = sum((Decimal(l.quantity) * Decimal(l.unit_cost_before) for l in receipt.lines.values()),
               ZERO)
    came_in = list(WarehouseProductItem.objects.select_for_update(of=("self",))
                   .select_related("product").filter(pk__in=receipt.came_in))
    total_in = sum((_left(r) for r in came_in), ZERO)
    if total_in <= 0:
        raise ProcessingError(_("Enter what came back from this supplier before receiving "
                                "the purchase."))
    touched = {}
    now = timezone.now()
    for roll_id, line in receipt.lines.items():
        line.received_at = now
        if roll_id in receipt.returned:
            line.outcome = "returned"
            line.quantity_back = receipt.returned[roll_id]
        else:
            roll = WarehouseProductItem.objects.select_related("product").get(pk=roll_id)
            StockMovement.objects.create(
                product=roll.product, stock_item=roll, movement_type="adjustment",
                quantity=-_left(roll),
                reason=f"{receipt.invoice.display_number}: used up in the work",
                reference=roll.barcode, created_by=user)
            roll.quantity_remaining = ZERO
            roll.status = "consumed"
            roll.processing_line = None
            roll.save(update_fields=["quantity_remaining", "status", "processing_line"])
            touched[roll.product_id] = roll.product
            line.outcome = "used"
            line.quantity_back = None
        line.save()

    share = pool / total_in
    for roll in came_in:
        roll.unit_cost_base = ((Decimal(roll.unit_cost_base or 0) + share)
                               .quantize(Decimal("0.0001")))
        roll.save(update_fields=["unit_cost_base"])
        touched[roll.product_id] = roll.product
    # What a unit of each row costs now, for the row's own "last cost".
    for roll in came_in:
        wp = touched[roll.product_id]
        wp.cost_usd = roll.unit_cost_base
        wp.save(update_fields=["cost_usd", "updated_at"])
    return list(touched.values())


# ── Undoing a receipt ────────────────────────────────────────────────────

def _in_use_since(roll, own_order_id=None):
    """Why a returned item can't be put back, or None. The order the
    purchase was bought for holding it, unpacked, is no reason: that hold
    goes with the receipt (unreceive_lines), as it does for the rolls the
    purchase brought in itself."""
    for hold in roll.reservations.select_related("order"):
        if hold.consumed:
            return _("it went out on order %(order)s.") % {"order": hold.order}
        if hold.pack_id:
            return _("it is packed for order %(order)s.") % {"order": hold.order}
        if hold.order_id != own_order_id:
            return _("it is held for order %(order)s.") % {"order": hold.order}
    if roll.quote_links.exists():
        return _("it is on a quote.")
    if roll.transfer_lines.exists():
        return _("it was moved to another book.")
    if roll.processing_line_id is not None:
        return _("it is away on another purchase.")
    return None


def unreceive_problems(invoice):
    """One line per out roll that can't be put back as it was."""
    problems = []
    for line in invoice.processing_lines.filter(received_at__isnull=False).select_related("stock_item"):
        roll = line.stock_item
        if roll is None:
            problems.append(f"{line.barcode}: " + _("it is gone."))
            continue
        if line.outcome == "returned":
            if _left(roll) != Decimal(line.quantity_back or 0):
                problems.append(f"{line.barcode}: " + _("%(qty)s has come off it since.") % {
                    "qty": format((Decimal(line.quantity_back or 0) - _left(roll)).normalize(), "f")})
                continue
            why = _in_use_since(roll, invoice.for_order_id)
            if why:
                problems.append(f"{line.barcode}: {why}")
        elif roll.status != "consumed" or _left(roll) != 0:
            problems.append(f"{line.barcode}: " + _("it has been changed since."))
    return problems


def unreceive_lines(invoice, *, user=None, keep_away=True):
    """Undo the receipt of the goods out: each roll goes back to the variant,
    length and cost it had. `keep_away` — the purchase is an order again,
    so they are away again (undo receipt); False when it is being cancelled
    and they are simply home. The goods-in rolls this purchase made are the
    caller's to remove. Must run inside the caller's transaction, after
    unreceive_problems() came back empty."""
    from operating.models import StockMovement, WarehouseProductItem
    from operating.views_warehouse import _move_roll, _recount_wp, _resync_wp_catalog

    touched = {}
    for line in (invoice.processing_lines.select_for_update(of=("self",))
                 .filter(received_at__isnull=False).select_related("from_product")):
        roll = (WarehouseProductItem.objects.select_for_update(of=("self",))
                .select_related("product").filter(pk=line.stock_item_id).first())
        if roll is None:
            continue
        # The order this purchase was bought for let go of it: it is going
        # back to what it was before the work.
        if invoice.for_order_id:
            roll.reservations.filter(order_id=invoice.for_order_id, consumed=False,
                                     pack__isnull=True).delete()
        source, target = roll.product, line.from_product
        if target is not None and target.pk != source.pk:
            _move_roll(roll, target, user=user,
                       reason_out=f"{invoice.display_number}: work undone — back to {target.sku}",
                       reason_in=f"{invoice.display_number}: work undone — was {source.sku}")
            touched[source.pk] = source
        if _left(roll) != Decimal(line.quantity):
            StockMovement.objects.create(
                product=target or source, stock_item=roll, movement_type="adjustment",
                quantity=Decimal(line.quantity) - _left(roll),
                reason=f"{invoice.display_number}: work undone",
                reference=roll.barcode, created_by=user)
        roll.quantity = line.length_before
        roll.quantity_remaining = line.quantity
        roll.status = line.status_before or "in_stock"
        roll.unit_cost_base = line.unit_cost_before
        roll.processing_line = line if keep_away else None
        roll.save(update_fields=["quantity", "quantity_remaining", "status",
                                 "unit_cost_base", "processing_line"])
        touched[roll.product_id] = roll.product
        line.received_at = None
        line.outcome = ""
        line.quantity_back = None
        line.save(update_fields=["received_at", "outcome", "quantity_back"])
    for wp in touched.values():
        _recount_wp(wp)
        _resync_wp_catalog(wp)


def away_summary(invoices):
    """Stamp `away_rolls`, `away_quantity` and `away_unit` on each purchase
    still sending rolls out — for "2 rolls away · 140 m" beside it in
    lists. The quantity is left out when the rolls are counted in more than
    one unit: meters and pieces don't add up."""
    from .models_processing import ProcessingLine

    by_invoice = {}
    for inv_id, qty, unit in (ProcessingLine.objects
                              .filter(invoice__in=[i.pk for i in invoices],
                                      received_at__isnull=True)
                              .values_list("invoice_id", "quantity", "unit")):
        row = by_invoice.setdefault(inv_id, {"n": 0, "q": ZERO, "units": set()})
        row["n"] += 1
        row["q"] += Decimal(qty or 0)
        row["units"].add(unit)
    for inv in invoices:
        row = by_invoice.get(inv.pk) if inv.status == "ordered" else None
        inv.away_rolls = row["n"] if row else 0
        one_unit = row is not None and len(row["units"]) == 1
        inv.away_quantity = row["q"] if one_unit else None
        inv.away_unit = next(iter(row["units"])) if one_unit else ""
    return invoices


def rolls_back_on(item):
    """Our own items that came back from the work as the variant of this
    purchase line, under their own barcode. They are still linked to the
    purchase that first bought them, so a line's own rolls never include
    them; its page and its labels add them (PurchaseOrderDetail,
    PurchaseItemLabels)."""
    from operating.models import WarehouseProductItem

    if not item.variant_id:
        return []
    return list(WarehouseProductItem.objects
                .filter(processing_history__invoice_id=item.invoice_id,
                        processing_history__outcome="returned",
                        product__catalog_variant_id=item.variant_id)
                .select_related("product", "product__warehouse",
                                "product__catalog_variant__product")
                .distinct().order_by("id"))
