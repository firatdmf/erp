"""Sending our own rolls to a supplier to be worked on, as purchase lines.

See models_processing for what a processing line is. The purchase form
posts them in its plan as

    "processing": [{"barcode": "KZL000123", "to_variant_id": 45,
                    "price": "1.20", "currency": "USD"}, ...]

and everything else follows from the purchase's own life:

  save (draft)   save_draft_lines()      the rolls are marked away
  confirm        receive_lines()         each roll becomes its new variant,
                                         its cost rises by the price
  undo receipt   unreceive_lines()       each roll goes back
  cancel         release_lines() /       a draft's rolls come back as they
                 unreceive_lines()       were; a received one's go back first

Every book works the same way: a line belongs to the purchase's book, and
only rolls on that book's shelves can be on it.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

ZERO = Decimal("0")


class ProcessingError(Exception):
    """A processing line that can't be saved or received, with a message
    for the person at the form. Nothing has been written."""


def plan_rows(plan):
    """The processing rows of a purchase plan, as posted."""
    rows = (plan or {}).get("processing") or []
    return [r for r in rows if isinstance(r, dict)]


def _decimal(value):
    try:
        return Decimal(str(value if value not in (None, "") else "0").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _left(roll):
    left = roll.quantity_remaining if roll.quantity_remaining is not None else roll.quantity
    return Decimal(left or 0)


def _find_roll(row):
    from operating.models import WarehouseProductItem

    qs = WarehouseProductItem.objects.select_related(
        "product", "product__warehouse", "product__catalog_variant__product")
    stock_id = str(row.get("stock_item_id") or "").strip()
    if stock_id.isdigit():
        return qs.filter(pk=int(stock_id)).first()
    code = (row.get("barcode") or "").strip()
    if not code:
        return None
    return WarehouseProductItem.matching_pick_key(qs, code).first()


def _roll_name(roll):
    return roll.barcode or f"#{roll.pk}"


def variant_label(variant):
    """"N1464T · pearl" — the SKU, and its values when they say more."""
    if variant is None:
        return ""
    values = [v.product_variant_attribute_value for v in
              variant.product_variant_attribute_values.all()
              if (v.product_variant_attribute_value or "").strip()]
    return " · ".join([variant.variant_sku or variant.product.title, *values[:3]])


def _describe(row):
    """One plan row read against the shelves and the catalog, with no
    judgement on whether it may be sent: roll, to_variant, from_variant,
    quantity, unit, price, currency. None when its roll or variant is not
    found or its price is not a number."""
    from marketing.models import ProductVariant

    roll = _find_roll(row)
    if roll is None:
        return None
    to_id = str(row.get("to_variant_id") or "").strip()
    to_variant = (ProductVariant.objects.select_related("product")
                  .filter(pk=int(to_id)).first() if to_id.isdigit() else None)
    from_variant = roll.product.catalog_variant
    return {
        "roll": roll, "to_variant": to_variant, "from_variant": from_variant,
        "quantity": _left(roll),
        "unit": (from_variant.product.unit if from_variant is not None else None) or "m",
        "price": _decimal(row.get("price")),
        "currency": (row.get("currency") or "USD").upper()[:3],
    }


def send_problem(roll, *, book, invoice=None):
    """Why `roll` can't be sent to be worked on, as a sentence naming it,
    or None: used up, on another book's shelves, held for an order, or
    already away on another purchase (`invoice` is the one being saved)."""
    name = _roll_name(roll)
    if roll.status == "consumed" or _left(roll) <= 0:
        return _("Roll %(code)s is used up — there is nothing on it to send.") % {"code": name}
    warehouse = roll.product.warehouse
    if book is not None and warehouse.accounting_book_id != book.pk:
        return (_("Roll %(code)s is on the shelves of %(book)s — send it on a purchase "
                  "of that book.") % {"code": name, "book": warehouse.accounting_book})
    holds = list(roll.reservations.filter(consumed=False).select_related("order"))
    if holds:
        orders = sorted({str(h.order.order_number or h.order_id) for h in holds})
        return (_("Roll %(code)s is reserved for order %(orders)s — take it off the order "
                  "before sending it.") % {"code": name, "orders": ", ".join(orders)})
    line = roll.processing_line
    if line is not None and (invoice is None or line.invoice_id != invoice.pk):
        return (_("Roll %(code)s is already away on purchase %(number)s.")
                % {"code": name, "number": line.invoice.display_number})
    return None


def lookup(code, *, book, invoice=None):
    """A roll as the purchase form shows it before it is sent: what it is,
    how much is on it, where, the variants of its product it can become,
    and why it can't be sent, if it can't. None when no roll has `code`."""
    roll = _find_roll({"barcode": code})
    if roll is None:
        return None
    wp = roll.product
    current = wp.catalog_variant
    product = current.product if current is not None else None
    variants = []
    if product is not None:
        for v in (product.variants.exclude(pk=current.pk)
                  .prefetch_related("product_variant_attribute_values")
                  .order_by("variant_sku")):
            variants.append({"id": v.pk, "sku": v.variant_sku or "", "label": variant_label(v)})
    return {
        "stock_item_id": roll.pk,
        "barcode": roll.barcode or "",
        "sku": (current.variant_sku if current is not None else None) or wp.sku or "",
        "label": variant_label(current) if current is not None else wp.name,
        "product": product.title if product is not None else wp.name,
        "quantity": format(_left(roll).normalize(), "f"),
        "unit": (product.unit if product is not None else None) or "m",
        "warehouse": wp.warehouse.name,
        "variants": variants,
        "problem": send_problem(roll, book=book, invoice=invoice),
    }


def resolve(plan, *, book, invoice=None):
    """Check the plan's processing rows against the shelves and the catalog.

    Returns one dict per row (see _describe). Raises ProcessingError naming
    the roll when a row can't be sent: not found, used up, in another
    book's warehouse, held for an order, already away on another purchase,
    sent twice here, a variant that isn't there, the variant it already is,
    or a product counted in another unit.
    """
    out, seen = [], set()
    for row in plan_rows(plan):
        r = _describe(row)
        if r is None:
            code = str(row.get("barcode") or row.get("stock_item_id") or "?").strip()
            raise ProcessingError(_("Roll %(code)s was not found.") % {"code": code})
        roll = r["roll"]
        name = _roll_name(roll)
        if roll.pk in seen:
            raise ProcessingError(_("Roll %(code)s is on this purchase twice.") % {"code": name})
        seen.add(roll.pk)
        problem = send_problem(roll, book=book, invoice=invoice)
        if problem:
            raise ProcessingError(problem)
        to_variant, from_variant = r["to_variant"], r["from_variant"]
        if to_variant is None:
            raise ProcessingError(_("Say what roll %(code)s is to become.") % {"code": name})
        if from_variant is not None and from_variant.pk == to_variant.pk:
            raise ProcessingError(
                _("Roll %(code)s is already %(sku)s — pick the variant it becomes.")
                % {"code": name, "sku": to_variant.variant_sku})
        if (to_variant.product.unit or "m") != r["unit"]:
            raise ProcessingError(
                _("Roll %(code)s is counted in %(unit)s and %(sku)s in %(other)s — it can "
                  "only become a variant counted the same way.")
                % {"code": name, "unit": r["unit"], "sku": to_variant.variant_sku,
                   "other": to_variant.product.unit})
        if r["price"] is None or r["price"] < 0:
            raise ProcessingError(_("The price for roll %(code)s is not a number.") % {"code": name})
        out.append(r)
    return out


def _line_description(from_variant, to_variant, fallback):
    return (_("Work: %(from)s → %(to)s") % {
        "from": variant_label(from_variant) or fallback,
        "to": variant_label(to_variant)})[:300]


def plan_lines(plan):
    """The purchase lines the processing rows bill: one per change of
    variant at one price, quantity summed over its rolls, in the shape
    views_purchase.plan_lines returns. Read leniently — a row that no
    longer describes anything is left out rather than refused: this also
    re-totals a draft from elsewhere, and saving is where rows are judged
    (resolve)."""
    groups = {}
    for row in plan_rows(plan):
        r = _describe(row)
        if r is None or r["to_variant"] is None or r["price"] is None:
            continue
        key = (r["from_variant"].pk if r["from_variant"] else None,
               r["to_variant"].pk, r["price"], r["currency"])
        if key not in groups:
            groups[key] = {
                "description": _line_description(r["from_variant"], r["to_variant"],
                                                 r["roll"].product.name),
                "quantity": ZERO, "unit": r["unit"][:20],
                "unit_price": r["price"], "currency": r["currency"],
                "product": None, "variant": None,
                "rolls": [], "processing": True, "pack_type": "",
                "sku": r["to_variant"].variant_sku or "",
                "parent_sku": r["to_variant"].product.sku or "",
                "attributes": [],
            }
        g = groups[key]
        g["quantity"] += r["quantity"]
        g["rolls"].append({"quantity": r["quantity"], "barcode": r["roll"].barcode or ""})
    return list(groups.values())


@transaction.atomic
def save_draft_lines(invoice, plan, *, user=None):
    """Make the draft's processing lines what its plan says: rolls taken
    off it come back, new ones go away, the rest take the new target and
    price. Raises ProcessingError, the caller rolling the save back."""
    from operating.models import WarehouseProductItem
    from .models_processing import ProcessingLine

    rows = resolve(plan, book=invoice.book, invoice=invoice)
    wanted = {r["roll"].pk: r for r in rows}
    # Lock every roll involved, old and new, before deciding anything.
    old = {line.stock_item_id: line for line in
           invoice.processing_lines.select_for_update().filter(received_at__isnull=True)}
    list(WarehouseProductItem.objects.select_for_update()
         .filter(pk__in=set(wanted) | {k for k in old if k}))

    for roll_id, line in old.items():
        if roll_id not in wanted:
            WarehouseProductItem.objects.filter(pk=roll_id, processing_line=line) \
                .update(processing_line=None)
            line.delete()
    for roll_id, r in wanted.items():
        line = old.get(roll_id) or ProcessingLine(invoice=invoice, stock_item=r["roll"])
        line.barcode = r["roll"].barcode or ""
        line.from_variant = r["from_variant"]
        line.to_variant = r["to_variant"]
        line.quantity = r["quantity"]
        line.unit = r["unit"]
        line.unit_price = r["price"]
        line.currency = r["currency"]
        line.save()
        WarehouseProductItem.objects.filter(pk=roll_id).update(processing_line=line)
    return rows


@transaction.atomic
def release_lines(invoice):
    """A draft cancelled: its rolls are back on the shelf as they were."""
    from operating.models import WarehouseProductItem

    lines = list(invoice.processing_lines.filter(received_at__isnull=True))
    WarehouseProductItem.objects.filter(processing_line__in=lines).update(processing_line=None)
    return lines


def _target_wp(warehouse, variant, source_wp):
    """The warehouse row of `variant` in `warehouse`, made when there is none."""
    from operating.models import WarehouseProduct

    wp = WarehouseProduct.objects.filter(warehouse=warehouse, catalog_variant=variant).first()
    if wp is None:
        wp = WarehouseProduct.objects.filter(warehouse=warehouse,
                                             sku__iexact=variant.variant_sku,
                                             catalog_variant__isnull=True).first()
        if wp is not None:
            wp.catalog_variant = variant
            wp.save(update_fields=["catalog_variant", "updated_at"])
    if wp is None:
        values = [v.product_variant_attribute_value for v in
                  variant.product_variant_attribute_values.all()]
        wp = WarehouseProduct.objects.create(
            warehouse=warehouse, catalog_variant=variant, sku=variant.variant_sku,
            name=(f"{variant.product.title} {' '.join(values)}".strip()
                  or variant.variant_sku)[:150],
            quantity=ZERO,
            cost_usd=source_wp.cost_usd, cost_try=source_wp.cost_try,
        )
    return wp


def receive_lines(invoice, *, user=None, rates=None):
    """The rolls are back, worked on: each moves onto the variant it became,
    in the warehouse it stands in, and costs what it did plus the price of
    the work. Returns the purchase lines to bill, as perform_intake
    collects them, each carrying the ids of its processing lines.

    Must run inside the caller's transaction. Raises ProcessingError."""
    from operating.models import WarehouseProductItem
    from operating.views_warehouse import (
        _PurchaseRates, _move_roll, _recount_wp, _resync_wp_catalog,
    )
    from .services_accounts import invoice_currency_for
    from .services_posting import stock_unit_cost

    lines = list(invoice.processing_lines.select_for_update(of=("self",))
                 .filter(received_at__isnull=True)
                 .select_related("to_variant__product", "from_variant"))
    if not lines:
        return []
    cost_rates = _PurchaseRates(invoice_currency_for(invoice.current_account), rates)
    rolls = {r.pk: r for r in WarehouseProductItem.objects.select_for_update(of=("self",))
             .select_related("product", "product__warehouse")
             .filter(pk__in=[l.stock_item_id for l in lines if l.stock_item_id])}
    touched, groups = {}, {}
    now = timezone.now()
    for line in lines:
        roll = rolls.get(line.stock_item_id)
        if roll is None or roll.processing_line_id != line.pk:
            raise ProcessingError(_("Roll %(code)s is no longer away on this purchase.")
                                  % {"code": line.barcode or "?"})
        added = ZERO
        if line.unit_price and line.unit_price > 0:
            added, _try = cost_rates.costs(Decimal(line.unit_price), line.currency)
            if added is None:
                raise ProcessingError(_("There is no exchange rate for %(currency)s to price "
                                        "the work on roll %(code)s.")
                                      % {"currency": line.currency, "code": line.barcode})
        before = stock_unit_cost(roll)
        source = roll.product
        target = _target_wp(source.warehouse, line.to_variant, source)
        if target.pk != source.pk:
            _move_roll(roll, target, user=user,
                       reason_out=f"{invoice.display_number}: worked on — now {target.sku}",
                       reason_in=f"{invoice.display_number}: worked on — was {source.sku}")
            touched[source.pk] = source
            touched[target.pk] = target
        roll.processing_line = None
        roll.unit_cost_base = (before or ZERO) + added
        roll.save(update_fields=["processing_line", "unit_cost_base"])

        line.received_at = now
        line.from_product = source
        line.unit_cost_before = before
        line.added_cost_base = added
        line.quantity = _left(roll)
        line.save(update_fields=["received_at", "from_product", "unit_cost_before",
                                 "added_cost_base", "quantity"])

        key = (line.from_variant_id, line.to_variant_id, line.unit_price, line.currency)
        g = groups.get(key)
        if g is None:
            g = groups[key] = {
                "description": _line_description(line.from_variant, line.to_variant,
                                                 source.name),
                "quantity": ZERO, "unit": line.unit, "unit_price": Decimal(line.unit_price),
                "currency": line.currency,
                # Not the variant's: these lines bill work, not goods, and
                # whatever reads a purchase's goods from its lines must
                # not count them.
                "product": None, "variant": None,
                "processing_line_ids": [],
            }
        g["quantity"] += Decimal(line.quantity)
        g["processing_line_ids"].append(line.pk)

    for wp in touched.values():
        _recount_wp(wp)
        _resync_wp_catalog(wp)
    return list(groups.values())


def link_invoice_items(purchase_lines, inv_items):
    """After the invoice is written: each processing line points at the
    invoice line that billed it (same order as purchase_lines)."""
    from .models_processing import ProcessingLine

    for line, item in zip(purchase_lines, inv_items):
        ids = line.get("processing_line_ids")
        if ids:
            ProcessingLine.objects.filter(pk__in=ids).update(invoice_item=item)


def roll_problem_since(line, roll):
    """Why a received line's roll can't be put back as it was, or None."""
    if roll is None:
        return _("the roll is gone.")
    if Decimal(roll.quantity_remaining if roll.quantity_remaining is not None
               else roll.quantity or 0) != Decimal(line.quantity):
        return _("%(qty)s has come off it since.") % {
            "qty": format((Decimal(line.quantity) - _left(roll)).normalize(), "f")}
    return _roll_in_use_after(roll)


def _roll_in_use_after(roll):
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
    """One line per roll that can't go back as it was, for the refusal."""
    lines = list(invoice.processing_lines.filter(received_at__isnull=False)
                 .select_related("stock_item"))
    problems = []
    for line in lines:
        why = roll_problem_since(line, line.stock_item)
        if why:
            problems.append(f"{line.barcode}: {why}")
    return problems


def unreceive_lines(invoice, *, user=None, keep_away=True):
    """Undo the receipt of the processing lines: each roll goes back to the
    variant and the cost it had. `keep_away` — the purchase is an order
    again, so the rolls are away again (undo receipt); False when the
    purchase is being cancelled and they are simply home.

    Must run inside the caller's transaction, after unreceive_problems()
    came back empty."""
    from operating.models import WarehouseProductItem
    from operating.views_warehouse import _move_roll, _recount_wp, _resync_wp_catalog

    lines = list(invoice.processing_lines.select_for_update(of=("self",))
                 .filter(received_at__isnull=False)
                 .select_related("from_product", "stock_item"))
    touched = {}
    for line in lines:
        roll = (WarehouseProductItem.objects.select_for_update(of=("self",))
                .select_related("product").filter(pk=line.stock_item_id).first())
        if roll is None:
            continue
        source = roll.product
        target = line.from_product
        if target is not None and target.pk != source.pk:
            _move_roll(roll, target, user=user,
                       reason_out=f"{invoice.display_number}: work undone — back to {target.sku}",
                       reason_in=f"{invoice.display_number}: work undone — was {source.sku}")
            touched[source.pk] = source
            touched[target.pk] = target
        roll.unit_cost_base = line.unit_cost_before
        roll.processing_line = line if keep_away else None
        roll.save(update_fields=["unit_cost_base", "processing_line"])
        line.received_at = None
        line.invoice_item = None
        line.save(update_fields=["received_at", "invoice_item"])
    for wp in touched.values():
        _recount_wp(wp)
        _resync_wp_catalog(wp)
    return lines
