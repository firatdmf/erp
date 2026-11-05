"""Purchases bought FOR a customer.

A client asks for something the shelves don't have, so it is ordered in from
a supplier. The purchase form names the customer and a sale price per
variant, and saving the purchase creates the customer's order alongside it
(accounting.Invoice.for_order). This module is everything that link means:

  * check_sale_prices —   what the customer pays is what the order line is
                          billed at, so no row may leave it blank;
  * put_plan_in_catalog — a draft purchase normally leaves no trace outside
                          its own document, but an order line must point at
                          a catalog product, so a purchase bought for a
                          customer puts its products and variants in the
                          catalog at save time — with the SKUs the receipt
                          will later find;
  * sync_customer_order — create the customer's order from the purchase, and
                          keep its lines in step while the draft is edited;
  * hold_received_rolls — when the purchase is received, its new rolls are
                          reserved for that order, so nobody packs them into
                          a different one first;
  * mirror_item_on_purchases, drop_purchase_lines_from_order,
    cancel_purchases_for_cancelled_order —
                          the link runs both ways: a line changed or removed
                          on the order changes the draft purchase, a purchase
                          cancelled takes its lines off the order, and either
                          document cancelled cancels the other when nothing
                          is left on it. Each side's change log says what the
                          other side did (operating.audit,
                          accounting.purchase_audit).

A reservation is the same soft hold the order form and the packing scan
create (OrderStockReservation): nothing is cut until the order ships.
"""
import copy
import threading
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation

from django.utils.translation import gettext as _

# While one side is writing the other, the OrderItem receivers that
# mirror the order onto its purchases stand down — otherwise a purchase
# edit would write the order, whose items would write the purchase back.
_sync_state = threading.local()


@contextmanager
def syncing():
    prev = getattr(_sync_state, "active", False)
    _sync_state.active = True
    try:
        yield
    finally:
        _sync_state.active = prev


def is_syncing():
    return getattr(_sync_state, "active", False)

# Orders that can no longer take a hold: shipped ones have already cut their
# stock, and a cancelled one never releases what it holds.
_CLOSED_STATUSES = {"shipped", "in_transit", "out_for_delivery", "delivered",
                    "cancelled", "returned"}


class CustomerOrderError(Exception):
    """The customer part of a purchase can't be saved. The message is
    user-facing."""


def packing_state(order):
    """Whether the packing floor has started on `order`, and how far —
    what the order's cancel confirmation says out loud before anyone
    confirms. Started means it has left "Open" or rolls are held for it."""
    status = order.order_status or "pending"
    rolls = order.stock_reservations.filter(consumed=False).count()
    return {
        "started": status != "pending" or rolls > 0,
        "rolls": rolls,
        "status": status,
        "status_label": order.get_order_status_display(),
    }


def held_line_ids(order):
    """The lines rolls are held for. Those stay as they are; every other
    line a purchase feeds follows the purchase until the order ships,
    packaging included — a shelf roll held for one line must not freeze
    the lines a purchase brings in (order 351 kept 3009 ecru 320 after its
    purchase turned 330, so the roll that came in matched nothing)."""
    return set(order.stock_reservations.filter(consumed=False)
               .values_list("order_item_id", flat=True))


def _line_skus(items):
    return ", ".join(sorted(it.product_variant.variant_sku or str(it.pk) for it in items))


def plan_quantities(plan):
    """{variant SKU, lowercased: quantity} a purchase plan brings in, its
    rows for one variant summed."""
    out = {}
    for p in ((plan or {}).get("products") or []):
        for v in (p.get("variants") or []):
            sku = (v.get("sku") or "").strip().lower()
            if sku:
                out[sku] = out.get(sku, Decimal("0")) + _row_quantity(v)
    return out


def other_purchase_quantities(order, invoice):
    """{variant SKU: quantity} the purchases bought for `order` other than
    `invoice` bring in, cancelled ones left out. A line fed by several
    purchases is the sum of them, so this is what a line comes to without
    `invoice`'s share."""
    total = {}
    for other in (order.supplier_purchases.exclude(status="cancelled")
                  .exclude(pk=invoice.pk).only("pk", "intake_plan")):
        for sku, qty in plan_quantities(other.intake_plan).items():
            total[sku] = total.get(sku, Decimal("0")) + qty
    return total


def purchase_locked_lines(order):
    """{order line pk: [draft purchases]} — the lines a purchase still on
    its way in feeds. The purchase owns them: their quantity is changed,
    and they are removed, on the purchase, and the order shows them
    read-only. Their price stays editable on either side (it is mirrored).

    A line rolls are held for is the order's again (held_line_ids — the
    purchase no longer rewrites it), and so is one whose purchases have
    all arrived: the received goods are what the order packs."""
    if not order_is_open(order):
        return {}
    drafts = list(order.supplier_purchases.filter(status="ordered")
                  .only("pk", "number", "intake_plan").order_by("pk"))
    if not drafts:
        return {}
    by_sku = {}
    for invoice in drafts:
        for sku in plan_variant_skus(invoice.intake_plan):
            by_sku.setdefault(sku, []).append(invoice)
    held = held_line_ids(order)
    locked = {}
    for item in order.items.select_related("product_variant"):
        if item.pk in held or not item.product_variant_id:
            continue
        invoices = by_sku.get((item.product_variant.variant_sku or "").lower())
        if invoices:
            locked[item.pk] = invoices
    return locked


def locked_line_error(item, invoices, *, removing=False):
    """What the order says when a line a purchase owns is changed on it."""
    what = {"sku": item.product_variant.variant_sku if item.product_variant_id else item.pk,
            "numbers": ", ".join(p.number for p in invoices)}
    if removing:
        return _("%(sku)s comes from purchase %(numbers)s — remove it there.") % what
    return _("%(sku)s comes from purchase %(numbers)s — change its quantity there.") % what


def purchase_cancel_warning(invoice):
    """What cancelling `invoice` will do to the customer order it was
    bought for, said before the cancel is confirmed: which of its lines
    come off, which stay because rolls are held for them, and whether the
    order is cancelled too. Empty when there is no open order to speak of."""
    order = invoice.for_order
    if order is None or invoice.status == "cancelled" or not order_is_open(order):
        return ""
    number = order.order_number or order.pk
    skus = plan_variant_skus(invoice.intake_plan)
    items = list(order.items.select_related("product_variant"))
    held = held_line_ids(order)
    others = other_purchase_quantities(order, invoice)
    ours = [it for it in items
            if it.product_variant_id and (it.product_variant.variant_sku or "").lower() in skus]
    # A line another purchase also brings stays, at that purchase's share.
    shared = [it for it in ours if it.pk not in held
              and others.get((it.product_variant.variant_sku or "").lower(), 0) > 0]
    going = [it for it in ours if it.pk not in held and it not in shared]
    staying = [it for it in ours if it.pk in held]
    if items and len(going) == len(items):
        return (_("Order %(number)s: all its lines come from this purchase, so the order "
                  "is cancelled too.") % {"number": number})
    warning = (_("Order %(number)s: its %(count)s line(s) from this purchase are removed; "
                 "the order stays open with the rest.")
               % {"number": number, "count": len(going)})
    if shared:
        warning += " " + (_("%(skus)s stay at what the other purchases bring.")
                          % {"skus": _line_skus(shared)})
    if staying:
        warning += " " + (_("Rolls are already held for %(skus)s, so those lines stay.")
                          % {"skus": _line_skus(staying)})
    return warning


def order_is_open(order):
    return (order.order_status or "pending") not in _CLOSED_STATUSES


def order_bought_for(invoice):
    """The customer order `invoice` is still bought for, or None.

    A cancelled order wants nothing any more: the goods bought for it are
    plain stock, so the purchase is edited, priced and received like one
    bought for the shelf — no sale price to ask for, no order to keep in
    step. The link itself (invoice.for_order) stays, as the record of why
    the goods were bought."""
    order = invoice.for_order
    if order is None or order.order_status == "cancelled":
        return None
    return order


def parse_customer(data):
    """The CRM contact or company a purchase form names, or None."""
    from crm.models import Company, Contact

    raw = data.get("customer") or {}
    kind = (raw.get("type") or "").strip()
    pk = str(raw.get("pk") or "").strip()
    if not kind and not pk:
        return None
    model = {"contact": Contact, "company": Company}.get(kind)
    customer = model.objects.filter(pk=int(pk)).first() if (model and pk.isdigit()) else None
    if customer is None:
        raise CustomerOrderError(_("The customer picked for this purchase was not found."))
    return customer


def _decimal(value):
    try:
        return Decimal(str(value if value not in (None, "") else "0").replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _row_quantity(v_in):
    """What one plan row brings in, over all its tops."""
    return sum((_decimal(t.get("qty")) for t in (v_in.get("tops") or [])),
               Decimal("0"))


def _plan_row_label(p_in, v_in, idx):
    """How a plan row is named when the plan is refused — from what was
    typed, because the catalog rows it would become don't exist yet."""
    from .views_warehouse import _row_label

    mp = p_in.get("main_product") or {}
    product = (mp.get("name") or mp.get("title") or "").strip()
    row = _row_label(v_in) or (v_in.get("sku") or "").strip()
    return " ".join(part for part in (product, row) if part) or \
        _("Row %(n)d") % {"n": idx}


def order_line_prices(order):
    """{variant SKU, lowercased: sale price} of `order`'s lines — the one
    sale price per item every purchase bought for the order follows."""
    if order is None:
        return {}
    return {(it.product_variant.variant_sku or "").lower(): it.price
            for it in order.items.select_related("product_variant")
            if it.product_variant_id and it.product_variant.variant_sku}


def align_plan_sale_prices(plan, order):
    """Put `order`'s sale price on every row of `plan` naming a variant the
    order already has a line for. The order owns the price: a purchase only
    sets it for a line it creates. Returns the SKUs whose typed price was
    replaced, so the save can say so."""
    prices = order_line_prices(order)
    replaced = []
    for p_in in ((plan or {}).get("products") or []):
        for v_in in (p_in.get("variants") or []):
            sku = (v_in.get("sku") or "").strip()
            price = prices.get(sku.lower())
            if price is None:
                continue
            if _decimal(v_in.get("sale_price")) != price:
                if _decimal(v_in.get("sale_price")) > 0:
                    replaced.append(sku)
                v_in["sale_price"] = str(price)
    return replaced


def check_sale_prices(plan, known=()):
    """Refuse a purchase bought for a customer that doesn't say what the
    customer pays for one of its rows.

    The sale price IS the order line's price — an empty box billed the
    customer 0.00, and nothing downstream says so: the order reads as a
    gift, and it is only questioned once the goods have arrived. The
    purchase price can't stand in for it, being the supplier's and usually
    in another currency.

    Rows with no quantity are not on the order, so they are not asked for;
    nor are rows of a variant the order already prices (`known`, lowercased
    SKUs) — those take the order's price.
    """
    missing = [
        _plan_row_label(p_in, v_in, idx)
        for p_in in (plan.get("products") or [])
        for idx, v_in in enumerate(p_in.get("variants") or [], start=1)
        if _row_quantity(v_in) > 0 and _decimal(v_in.get("sale_price")) <= 0
        and (v_in.get("sku") or "").strip().lower() not in known
    ]
    if missing:
        raise CustomerOrderError(
            _("A purchase bought for a customer needs the price the customer "
              "is charged on every item. Missing on: %(rows)s")
            % {"rows": ", ".join(missing)})


def put_plan_in_catalog(plan, order=None):
    """Create the catalog products and variants a draft purchase names, and
    rewrite `plan` in place to point at them — each card as an existing
    product, each variant row with the SKU it was given — so confirming the
    draft later lands its rolls on these same variants instead of minting
    new ones.

    Returns one {"product", "variant", "quantity", "sale_price"} per variant
    row that has a quantity. Raises IntakeError on the same validation
    failures a receipt would, and CustomerOrderError on a row that names no
    sale price — checked here, before any catalog row is written, because
    every path that makes a customer order comes through this function.
    """
    from .catalog_sync import CatalogSyncConflict, sync_roll_to_catalog
    from .views_warehouse import (
        IntakeError, _apply_sku_choices, _intake_account, _intake_main_product,
        _intake_check_described, _intake_check_lookalikes, _intake_prefix,
        _intake_resolve_products,
        _intake_variant_identity, _row_label,
        _intake_variants,
    )

    check_sale_prices(plan, known=set(order_line_prices(order)))
    products_in = plan.get("products") or []
    _apply_sku_choices(products_in)
    account = _intake_account(plan)
    prefix = _intake_prefix(plan, account.name)
    resolved = _intake_resolve_products(products_in, prefix,
                                        default_unit=plan.get("unit"))
    _intake_check_described(products_in)
    _intake_check_lookalikes(resolved)

    lines = []
    for p_in, item in zip(products_in, resolved):
        main_product = _intake_main_product(item, prefix)
        p_in["main_product"] = {"mode": "existing", "id": main_product.pk,
                                "title": main_product.title,
                                "name": main_product.title,
                                "sku": main_product.sku or ""}
        seen = set()
        rows = _intake_variants(item, main_product)
        for idx, (v_in, v) in enumerate(zip(p_in.get("variants") or [], rows), start=1):
            qty = _row_quantity(v)
            if not _row_label(v) and not (v.get("sku") or "").strip() and qty <= 0:
                continue
            ident = _intake_variant_identity(main_product, item["base_name"], v, idx, seen)
            try:
                _p, variant, _pc, _vc = sync_roll_to_catalog(
                    base_name=item["base_name"],
                    attributes=ident["attributes"],
                    variant_sku=ident["sku"],
                    existing_base_product=main_product,
                    refuse_lookalike=True,
                )
            except CatalogSyncConflict as exc:
                raise IntakeError({"success": False, "error": f"{ident['sku']}: {exc}"},
                                  status=400)
            # Stamped on every row, including a card with no variants —
            # its implicit variant is the product itself, and a plan that
            # doesn't name it leaves plan_variant_skus blind to the line it
            # put on the order (see there).
            v_in["sku"] = variant.variant_sku
            if qty > 0:
                lines.append({"product": main_product, "variant": variant,
                              "quantity": qty,
                              "sale_price": _decimal(v_in.get("sale_price"))})
    return lines


def plan_variant_skus(plan):
    """The variant SKUs a saved purchase plan put on its customer order."""
    return {(v.get("sku") or "").strip().lower()
            for p in ((plan or {}).get("products") or [])
            for v in (p.get("variants") or []) if (v.get("sku") or "").strip()}


def plan_expected_rolls(plan, sku):
    """Each roll a purchase plan expects for `sku`, as (barcode, quantity)
    — a guess until the goods arrive and the receipt re-enters them. The
    barcode is "" until someone gives the roll one; the receipt mints it."""
    sku = (sku or "").strip().lower()
    return [((t.get("barcode") or "").strip(), q)
            for p in ((plan or {}).get("products") or [])
            for v in (p.get("variants") or [])
            if sku and (v.get("sku") or "").strip().lower() == sku
            for t in (v.get("tops") or []) if isinstance(t, dict)
            for q in [_decimal(t.get("qty"))] if q > 0]


def sync_customer_order(invoice, customer, lines, *, book, member=None, previous_skus=()):
    """Create the customer order `invoice` is bought for, or bring its
    lines in step with the purchase. Returns a user-facing warning when the
    order could not be changed, else None.

    Lines are matched by variant. A line fed by several purchases comes to
    their sum: this purchase's rows plus what the order's other purchases
    bring of that variant. A line is only removed when this purchase put it
    there (`previous_skus`, from the plan as last saved) and no other
    purchase still brings it — then it falls back to what the others bring;
    anything added on the order itself is the order's business. The lines
    follow until the order ships, packaging included; a shipped order is
    left as it is. So, for now, is a line rolls are already held for — the
    other lines still follow — and the purchase names it rather than
    rewriting it under the packers.
    """
    from accounting.services_accounts import (
        get_or_create_current_account_for_order, post_order_movement,
        stamp_order_currency,
    )
    from .models import Order, OrderItem
    from .views import _as_line_decimal, generate_machine_qr_for_order

    order = invoice.for_order
    if order is None:
        if customer is None:
            return None
        # No note naming the supplier: notes print on the customer's copy
        # of the order, and who we buy from is not theirs to read. The
        # link lives on invoice.for_order, which the order page shows
        # under "Supplier purchases".
        order = Order()
        if customer._meta.model_name == "company":
            order.company = customer
        else:
            order.contact = customer
        order.save()
        invoice.for_order = order
        invoice.save(update_fields=["for_order", "updated_at"])
        created = True
    else:
        created = False
        if not order_is_open(order):
            return (_("Order %(number)s has already shipped, so its lines were not "
                      "changed — reopen it to change them.")
                    % {"number": order.order_number or order.pk})

    from .audit import log_change

    existing = {it.product_variant_id: it
                for it in order.items.select_related("product_variant")}
    previous = {s.lower() for s in previous_skus}
    held = set() if created else held_line_ids(order)
    others = {} if created else other_purchase_quantities(order, invoice)
    kept = []   # lines this save would have changed, left for their held rolls
    # One entry per variant: two rows of one variant on this purchase are
    # one line on the order, their quantities summed.
    merged = {}
    for line in lines:
        entry = merged.setdefault(line["variant"].pk, dict(line, quantity=Decimal("0")))
        entry["quantity"] += _decimal(line["quantity"])
        entry["sale_price"] = line["sale_price"]
    wanted = set()
    changed = 0
    with syncing():
        for line in merged.values():
            variant = line["variant"]
            wanted.add(variant.pk)
            item = existing.get(variant.pk)
            sku = (variant.variant_sku or "").lower()
            qty = _as_line_decimal(line["quantity"] + others.get(sku, Decimal("0")))
            price = _as_line_decimal(line["sale_price"])
            if item is None:
                OrderItem.objects.create(order=order, product=line["product"],
                                         product_variant=variant,
                                         quantity=qty, price=price)
                changed += 1
            elif item.quantity != qty:
                # Only the quantity: the sale price is the order's, one per
                # line, and the purchase follows it (align_plan_sale_prices).
                if item.pk in held:
                    kept.append(item)
                    continue
                item.quantity = qty
                item.save(update_fields=["quantity"])
                changed += 1
        for variant_id, item in existing.items():
            sku = (item.product_variant.variant_sku or "").lower() if item.product_variant_id else ""
            if variant_id not in wanted and sku in previous:
                rest = _as_line_decimal(others.get(sku, Decimal("0")))
                if rest > 0 and item.quantity == rest:
                    continue
                if item.pk in held:
                    kept.append(item)
                    continue
                if rest > 0:
                    # Another purchase still brings it: the line is theirs.
                    item.quantity = rest
                    item.save(update_fields=["quantity"])
                else:
                    item.delete()
                changed += 1
    if changed and not created:
        # The item rows above are logged by operating.audit as they
        # happen; this row says where they came from.
        log_change(order, "field", field="purchase",
                   new=_("%(count)s line(s) changed from purchase %(number)s")
                   % {"count": changed, "number": invoice.number})

    if created:
        account = get_or_create_current_account_for_order(order, member=member, book=book)
        if account is not None:
            order.current_account = account
            order.save(update_fields=["current_account"])
            # The sale prices on the purchase form are stated in this
            # account's currency, so the order must say so too — otherwise
            # they are read as dollars by everything downstream.
            stamp_order_currency(order, account)
        try:
            generate_machine_qr_for_order(order)
        except Exception:
            # A QR upload hiccup must not lose the purchase; the order
            # page can still be printed without it.
            pass
    post_order_movement(order, member=member)
    if kept:
        return (_("Order %(number)s: rolls are already held for %(skus)s, so those lines "
                  "were not changed — edit them on the order.")
                % {"number": order.order_number or order.pk, "skus": _line_skus(kept)})
    return None


def hold_received_rolls(invoice, *, user=None):
    """Reserve the rolls `invoice` brought in for the order it was bought
    for — each one whole, onto the line of its variant.

    Whole, not up to what the line asked for: the customer ordered about
    so much, and what was bought for them is theirs, so a roll that came
    in longer than ordered goes with the order rather than leaving a
    remnant on the shelf.

    Only the line of the roll's own variant takes it. The packing scan's
    looser matches (a variant-less line of the same product, a bare SKU)
    suit a person at the table who sees what they bound; holding whole
    rolls unseen, they would hand one variant's rolls to another's line.
    The purchase put its rows in the catalog as variants before the order
    lines were made from them, so its rolls and its lines share one.
    Rolls that match no line stay free stock. Returns one {"barcode",
    "quantity", "line"} per hold made. Safe to call again: a roll the
    order already holds is skipped.
    """
    from .models import OrderStockReservation, WarehouseProductItem
    from .views import _create_roll_reservation

    order = invoice.for_order
    if order is None or not order_is_open(order):
        return []
    lines = {}
    for it in order.items.filter(product_variant__isnull=False).order_by("pk"):
        lines.setdefault(it.product_variant_id, it)
    if not lines:
        return []
    already = set(OrderStockReservation.objects
                  .filter(order=order, consumed=False)
                  .values_list("stock_item_id", flat=True))
    rolls = (WarehouseProductItem.objects
             .filter(purchase_invoice_item__invoice=invoice)
             .exclude(pk__in=already)
             .select_related("product")
             .order_by("pk"))
    held = []
    for roll in rolls:
        line = lines.get(roll.product.catalog_variant_id) if roll.product_id else None
        if line is None:
            continue
        r, _capped, err = _create_roll_reservation(order, line, roll, None, user)
        if err or r is None:
            continue
        held.append({"barcode": roll.barcode, "quantity": r.quantity,
                     "line": line.pk})
    return held


# ── The order writes the purchase ────────────────────────────────────

def _retops(v_in, quantity):
    """Make a plan row's rolls add up to `quantity`. Less: trimmed from
    the last roll back. More: one more roll for the difference. The rolls
    are a guess until the goods arrive, and the receipt re-enters them."""
    tops = [t for t in (v_in.get("tops") or []) if isinstance(t, dict)]
    total = sum((_decimal(t.get("qty")) for t in tops), Decimal("0"))
    if quantity > total:
        tops.append({"qty": str(quantity - total), "barcode": ""})
    elif quantity < total:
        excess = total - quantity
        while excess > 0 and tops:
            last = tops[-1]
            q = _decimal(last.get("qty"))
            if q <= excess and len(tops) > 1:
                tops.pop()
                excess -= q
            else:
                last["qty"] = str(max(q - excess, Decimal("0")))
                excess = Decimal("0")
    v_in["tops"] = tops


def _plan_has_rows(plan):
    return any(_row_quantity(v) > 0
               for p in (plan or {}).get("products") or []
               for v in p.get("variants") or [])


def _auth_user(user):
    """apply_order_status_change is handed a Member from one call site and
    a User from the rest; the purchase side wants the User."""
    if user is None or hasattr(user, "is_authenticated"):
        return user
    return getattr(user, "user", None)


def mirror_item_on_purchases(item, *, removed=False, user=None):
    """A line changed on the order: put the same change on every draft
    purchase that names its variant — quantity and sale price on an edit,
    the row itself on a removal. A purchase left with nothing to buy is
    cancelled. Lines the order adds on its own are NOT put on a purchase:
    the order doesn't know a cost price, and they may well be stock.

    A received purchase is stock now: its rows stay what arrived, and only
    the sale price follows (_mirror_sale_price_on_received), so the
    purchase and the order never disagree about what the customer pays."""
    if is_syncing():
        return
    from accounting.purchase_audit import diff_plans
    from accounting.views_purchase import cancel_purchase_invoice, rewrite_draft_plan
    from .audit import log_change

    order = item.order
    variant = item.product_variant
    sku = (variant.variant_sku if variant is not None else "").strip().lower()
    if not sku:
        return
    # A line fed by several purchases is their sum, so an order-side
    # quantity can't be split back among them: it reaches a purchase only
    # when that purchase is the line's one source. (The order refuses
    # quantity edits on such lines anyway — purchase_locked_lines; this
    # covers the system writes, like a held roll re-measured.)
    sources = [inv for inv in order.supplier_purchases.exclude(status="cancelled")
               .only("pk", "intake_plan")
               if sku in plan_variant_skus(inv.intake_plan)]
    one_source = len(sources) <= 1
    for invoice in (order.supplier_purchases.filter(status="ordered")
                    .select_related("current_account")):
        before = copy.deepcopy(invoice.intake_plan or {})
        plan = copy.deepcopy(before)
        hit = False
        for p_in in plan.get("products") or []:
            kept = []
            for v_in in p_in.get("variants") or []:
                if (v_in.get("sku") or "").strip().lower() != sku:
                    kept.append(v_in)
                    continue
                hit = True
                if removed:
                    continue
                v_in["sale_price"] = str(item.price)
                if one_source:
                    _retops(v_in, _decimal(item.quantity))
                kept.append(v_in)
            p_in["variants"] = kept
        if not hit:
            continue
        plan["products"] = [p for p in plan.get("products") or [] if p.get("variants")]
        with syncing():
            diff_plans(invoice, before, plan, origin="order", user=user)
            if _plan_has_rows(plan):
                rewrite_draft_plan(invoice, plan)
            else:
                # Nothing left to buy. The plan is kept as it was so the
                # cancelled purchase still reads what it was for.
                cancel_purchase_invoice(
                    invoice.pk, user, origin="order", mirror_order=False,
                    reason=_("Nothing left on it to buy — the lines were removed from order %(number)s")
                    % {"number": order.order_number or order.pk})
                log_change(order, "field", field="purchase",
                           new=_("%(number)s cancelled — nothing left on it to buy")
                           % {"number": invoice.number})
    if not removed:
        _mirror_sale_price_on_received(order, sku, item.price, user=user)


def _mirror_sale_price_on_received(order, sku, price, *, user=None):
    """Put the order line's price on the rows naming `sku` in the plans of
    the received purchases bought for `order`. The plan is the purchase's
    record of what it said; nothing else about it changes."""
    from accounting.purchase_audit import diff_plans
    from accounting.models import Invoice

    for invoice in order.supplier_purchases.exclude(status__in=("ordered", "cancelled")):
        before = invoice.intake_plan or {}
        plan = copy.deepcopy(before)
        hit = False
        for p_in in plan.get("products") or []:
            for v_in in p_in.get("variants") or []:
                if ((v_in.get("sku") or "").strip().lower() == sku
                        and _decimal(v_in.get("sale_price")) != price):
                    v_in["sale_price"] = str(price)
                    hit = True
        if not hit:
            continue
        with syncing():
            diff_plans(invoice, before, plan, origin="order", user=user)
            Invoice.objects.filter(pk=invoice.pk).update(intake_plan=plan)


def order_sale_prices(invoice):
    """What the order `invoice` is bought for charges per variant,
    {variant_id: price} — the sale price a received purchase's form shows,
    read from the order because the order line IS that price. Empty when
    the purchase is bought for no open order."""
    order = order_bought_for(invoice)
    if order is None:
        return {}
    return {it.product_variant_id: it.price
            for it in order.items.all() if it.product_variant_id}


def cancel_purchases_for_cancelled_order(order, *, user=None, deleted=False):
    """The order is being cancelled (or deleted — `deleted`): stock
    ordered in for it is no longer wanted, so its draft purchases are
    cancelled with it. A received purchase is stock on the shelf and
    stays. Returns the numbers of the purchases cancelled.

    A deleted order takes its own log with it, so the purchase's log is
    told the order is gone — otherwise the cancel row would point at an
    order nobody can open."""
    from accounting.purchase_audit import log_purchase
    from accounting.views_purchase import cancel_purchase_invoice
    from .audit import log_change

    user = _auth_user(user)
    cancelled = []
    for invoice in list(order.unreceived_purchases()):
        with syncing():
            cancel_purchase_invoice(
                invoice.pk, user, origin="order", mirror_order=False,
                reason=(_("Order %(number)s was deleted") if deleted
                        else _("Order %(number)s was cancelled"))
                % {"number": order.order_number or order.pk})
        if deleted:
            log_purchase(invoice, "field", field="order", origin="order", user=user,
                         new=_("Order %(number)s deleted — this purchase was cancelled with it")
                         % {"number": order.order_number or order.pk})
        else:
            log_change(order, "field", field="purchase",
                       new=_("%(number)s cancelled with the order") % {"number": invoice.number})
        cancelled.append(invoice.number)
    return cancelled


def drop_purchase_lines_from_order(invoice, *, user=None):
    """The purchase was cancelled on its own page: take the lines it put
    on the customer's order off again, and cancel an order left empty.
    Returns the sentence the purchase page shows about the order, or None
    when there is nothing to say."""
    from .audit import log_change
    from .models import Order, OrderChange
    from .views import _as_line_decimal
    from .views_warehouse import apply_order_status_change

    order = invoice.for_order
    if order is None or not order_is_open(order):
        return None
    number = order.order_number or order.pk
    skus = plan_variant_skus(invoice.intake_plan)
    held = held_line_ids(order)
    others = other_purchase_quantities(order, invoice)
    removed = 0
    kept = []
    lowered = []    # lines other purchases still bring: down to their share
    with syncing():
        for item in order.items.select_related("product_variant"):
            sku = (item.product_variant.variant_sku or "").lower() if item.product_variant_id else ""
            if sku in skus:
                if item.pk in held:
                    kept.append(item)
                    continue
                rest = _as_line_decimal(others.get(sku, Decimal("0")))
                if rest > 0:
                    if item.quantity != rest:
                        item.quantity = rest
                        item.save(update_fields=["quantity"])
                    lowered.append(item)
                    continue
                item.delete()
                removed += 1
        log_change(order, "field", field="purchase",
                   new=_("%(number)s cancelled — %(count)s line(s) removed")
                   % {"number": invoice.number, "count": removed})
        if order.items.exists():
            said = (_("Its %(count)s line(s) were removed from order %(number)s, which "
                      "stays open with what else is on it.")
                    % {"count": removed, "number": number})
            if lowered:
                said += " " + (_("%(skus)s stay at what the other purchases bring.")
                               % {"skus": _line_skus(lowered)})
            if kept:
                said += " " + (_("Rolls are already held for %(skus)s, so those lines stay.")
                               % {"skus": _line_skus(kept)})
            return said
        # A half of a split order emptied while another half still has goods
        # on it: only this half is called off. The status funnel moves every
        # half together, so it would cancel the goods the customer still
        # wants. Nobody is told — the order itself goes ahead.
        rest_goes_ahead = bool(order.split_group) and (
            Order.objects.filter(split_group=order.split_group, items__isnull=False)
            .exclude(pk=order.pk).exclude(order_status="cancelled").exists())
        if rest_goes_ahead:
            from .views_warehouse import _apply_status_to_one
            order._one_notice_for_split = True
            ok, _code = _apply_status_to_one(order, "cancelled", user=user)
        else:
            ok, _code = apply_order_status_change(order, "cancelled", user=user)
    if not ok:
        return (_("Order %(number)s has nothing left on it but could not be cancelled "
                  "— cancel it on the order page.") % {"number": number})
    OrderChange.objects.create(
        order=order, action="field", field="cancel_reason",
        new_value=_("Purchase %(number)s cancelled") % {"number": invoice.number},
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    if rest_goes_ahead:
        return (_("Order %(number)s had nothing else on it and was cancelled too. "
                  "The rest of the split order stays open.") % {"number": number})
    return (_("Order %(number)s had nothing else on it and was cancelled too.")
            % {"number": number})
