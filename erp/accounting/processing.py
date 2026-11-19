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


def _find_roll(row):
    from operating.models import WarehouseProductItem

    qs = WarehouseProductItem.objects.select_related(
        "product", "product__warehouse", "product__catalog_variant__product",
        "processing_line__invoice")
    stock_id = str(row.get("stock_item_id") or "").strip()
    if stock_id.isdigit():
        return qs.filter(pk=int(stock_id)).first()
    code = str(row.get("barcode") or "").strip()
    if not code:
        return None
    return WarehouseProductItem.matching_pick_key(qs, code).first()


def _roll_name(roll):
    return roll.barcode or f"#{roll.pk}"


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


def send_problem(roll, *, book, invoice=None):
    """Why `roll` can't go out to be worked on, as a sentence naming it, or
    None: used up, on another book's shelves, held for an order, or already
    away on another purchase (`invoice` is the one being saved)."""
    name = _roll_name(roll)
    if roll.status == "consumed" or _left(roll) <= 0:
        return _("%(code)s is used up — there is nothing left of it to send.") % {"code": name}
    warehouse = roll.product.warehouse
    if book is not None and warehouse.accounting_book_id != book.pk:
        return (_("%(code)s is on the shelves of %(book)s — send it on a purchase "
                  "of that book.") % {"code": name, "book": warehouse.accounting_book})
    holds = list(roll.reservations.filter(consumed=False).select_related("order"))
    if holds:
        orders = sorted({str(h.order.order_number or h.order_id) for h in holds})
        return (_("%(code)s is reserved for order %(orders)s — take it off the order "
                  "before sending it.") % {"code": name, "orders": ", ".join(orders)})
    line = roll.processing_line
    if line is not None and (invoice is None or line.invoice_id != invoice.pk):
        return (_("%(code)s is already away on purchase %(number)s.")
                % {"code": name, "number": line.invoice.display_number})
    return None


def lookup(code, *, book, invoice=None):
    """A roll as the purchase form shows it in goods out: what it is, how
    much is on it, where, and why it can't go, if it can't. None when no
    roll has `code`."""
    roll = _find_roll({"barcode": code})
    if roll is None:
        return None
    wp = roll.product
    variant = wp.catalog_variant
    return {
        "stock_item_id": roll.pk,
        "barcode": roll.barcode or "",
        "sku": (variant.variant_sku if variant is not None else None) or wp.sku or "",
        "label": variant_label(variant) if variant is not None else wp.name,
        "quantity": format(_left(roll).normalize(), "f"),
        "unit": _unit(roll),
        "warehouse": wp.warehouse.name,
        "problem": send_problem(roll, book=book, invoice=invoice),
    }


def resolve(plan, *, book, invoice=None):
    """The plan's goods-out rolls, checked. Raises ProcessingError naming
    the roll when one can't go: not found, sent twice, or any of
    send_problem's reasons."""
    out, seen = [], set()
    for row in plan_rows(plan):
        roll = _find_roll(row)
        if roll is None:
            code = str(row.get("barcode") or row.get("stock_item_id") or "?").strip()
            raise ProcessingError(_("Nothing in stock has the barcode %(code)s.") % {"code": code})
        if roll.pk in seen:
            raise ProcessingError(_("%(code)s is on this purchase twice.")
                                  % {"code": _roll_name(roll)})
        seen.add(roll.pk)
        problem = send_problem(roll, book=book, invoice=invoice)
        if problem:
            raise ProcessingError(problem)
        out.append(roll)
    return out


@transaction.atomic
def save_draft_lines(invoice, plan, *, user=None):
    """Make the draft's goods out what its plan says: rolls taken off it
    come home, new ones go away. Raises ProcessingError, the caller rolling
    the save back."""
    from operating.models import WarehouseProductItem
    from .models_processing import ProcessingLine

    rolls = {r.pk: r for r in resolve(plan, book=invoice.book, invoice=invoice)}
    old = {line.stock_item_id: line for line in
           invoice.processing_lines.select_for_update().filter(received_at__isnull=True)}
    list(WarehouseProductItem.objects.select_for_update()
         .filter(pk__in=set(rolls) | {k for k in old if k}))

    for roll_id, line in old.items():
        if roll_id not in rolls:
            WarehouseProductItem.objects.filter(pk=roll_id, processing_line=line) \
                .update(processing_line=None)
            line.delete()
    for roll_id, roll in rolls.items():
        line = old.get(roll_id) or ProcessingLine(invoice=invoice, stock_item=roll)
        line.barcode = roll.barcode or ""
        line.quantity = _left(roll)
        line.unit = _unit(roll)
        line.save()
        WarehouseProductItem.objects.filter(pk=roll_id).update(processing_line=line)
    return list(rolls.values())


@transaction.atomic
def release_lines(invoice):
    """A draft cancelled: its out rolls are back on the shelf as they were."""
    from operating.models import WarehouseProductItem

    lines = list(invoice.processing_lines.filter(received_at__isnull=True))
    WarehouseProductItem.objects.filter(processing_line__in=lines).update(processing_line=None)
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

def _in_use_since(roll):
    for hold in roll.reservations.select_related("order"):
        if hold.consumed:
            return _("it went out on order %(order)s.") % {"order": hold.order}
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
            why = _in_use_since(roll)
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
