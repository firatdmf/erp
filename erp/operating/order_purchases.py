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


def order_is_open(order):
    return (order.order_status or "pending") not in _CLOSED_STATUSES


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


def check_sale_prices(plan):
    """Refuse a purchase bought for a customer that doesn't say what the
    customer pays for one of its rows.

    The sale price IS the order line's price — an empty box billed the
    customer 0.00, and nothing downstream says so: the order reads as a
    gift, and it is only questioned once the goods have arrived. The
    purchase price can't stand in for it, being the supplier's and usually
    in another currency.

    Rows with no quantity are not on the order, so they are not asked for.
    """
    missing = [
        _plan_row_label(p_in, v_in, idx)
        for p_in in (plan.get("products") or [])
        for idx, v_in in enumerate(p_in.get("variants") or [], start=1)
        if _row_quantity(v_in) > 0 and _decimal(v_in.get("sale_price")) <= 0
    ]
    if missing:
        raise CustomerOrderError(
            _("A purchase bought for a customer needs the price the customer "
              "is charged on every item. Missing on: %(rows)s")
            % {"rows": ", ".join(missing)})


def put_plan_in_catalog(plan):
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
        IntakeError, _intake_account, _intake_main_product,
        _intake_check_lookalikes, _intake_prefix, _intake_resolve_products,
        _intake_variant_identity, _row_label,
        _intake_variants,
    )

    check_sale_prices(plan)
    products_in = plan.get("products") or []
    account = _intake_account(plan)
    prefix = _intake_prefix(plan, account.name)
    resolved = _intake_resolve_products(products_in, prefix,
                                        default_unit=plan.get("unit"))
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


def sync_customer_order(invoice, customer, lines, *, book, member=None, previous_skus=()):
    """Create the customer order `invoice` is bought for, or bring its
    lines in step with the purchase. Returns a user-facing warning when the
    order could not be changed, else None.

    Lines are matched by variant. A line is only removed when this purchase
    put it there (`previous_skus`, from the plan as last saved) — anything
    added on the order itself is the order's business. An order that has
    left "Open", or that already holds rolls, belongs to the packing floor
    now: it is left as it is and the purchase says so rather than rewriting
    it under them.
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
        if (order.order_status or "pending") != "pending" or \
                order.stock_reservations.filter(consumed=False).exists():
            return (_("Order %(number)s is already being packed, so its lines were not "
                      "changed — edit them on the order.")
                    % {"number": order.order_number or order.pk})

    from .audit import log_change

    existing = {it.product_variant_id: it
                for it in order.items.select_related("product_variant")}
    previous = {s.lower() for s in previous_skus}
    wanted = set()
    changed = 0
    with syncing():
        for line in lines:
            variant = line["variant"]
            wanted.add(variant.pk)
            item = existing.get(variant.pk)
            qty = _as_line_decimal(line["quantity"])
            price = _as_line_decimal(line["sale_price"])
            if item is None:
                OrderItem.objects.create(order=order, product=line["product"],
                                         product_variant=variant,
                                         quantity=qty, price=price)
                changed += 1
            elif item.quantity != qty or item.price != price:
                item.quantity, item.price = qty, price
                item.save(update_fields=["quantity", "price"])
                changed += 1
        for variant_id, item in existing.items():
            sku = (item.product_variant.variant_sku or "").lower() if item.product_variant_id else ""
            if variant_id not in wanted and sku in previous:
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
        order.original_snapshot = order.build_snapshot()
        order.save(update_fields=["original_snapshot"])
        try:
            generate_machine_qr_for_order(order)
        except Exception:
            # A QR upload hiccup must not lose the purchase; the order
            # page can still be printed without it.
            pass
    post_order_movement(order, member=member)
    return None


def _line_required(item):
    """What a line needs in stock units — curtains count fabric, not
    curtains (same rule as order_reservation_shortfalls)."""
    required = item.quantity or Decimal("0")
    if getattr(item, "is_custom_curtain", False) and item.custom_fabric_used_meters:
        required = item.custom_fabric_used_meters
    return Decimal(str(required))


def _reserved_by_line(order):
    from django.db.models import Sum
    from .models import OrderStockReservation

    return {
        r["order_item_id"]: (r["s"] or Decimal("0"))
        for r in (OrderStockReservation.objects
                  .filter(order=order, consumed=False, order_item__isnull=False)
                  .values("order_item_id").annotate(s=Sum("quantity")))
    }


def _line_need(item, reserved):
    """What a line still has to get from a roll: ordered, minus what rolls
    already hold, minus what is sourced outside the warehouse."""
    need = (_line_required(item)
            - reserved.get(item.pk, Decimal("0"))
            - (item.outsourced_quantity or Decimal("0")))
    return need if need > 0 else Decimal("0")


def hold_received_rolls(invoice, *, user=None):
    """Reserve the rolls `invoice` brought in for the order it was bought
    for, up to what each order line still needs.

    Rolls that match no line of the order, or arrive after the line is
    covered, stay free stock. Returns one {"barcode", "quantity", "line"}
    per hold made. Safe to call again: a roll the order already holds is
    skipped, and a covered line takes nothing more.
    """
    from .models import OrderStockReservation, WarehouseProductItem
    from .views import (
        _create_roll_reservation, _match_roll_to_order, _order_item_match_maps,
    )

    order = invoice.for_order
    if order is None or not order_is_open(order):
        return []
    items, variant_ids, product_ids, skus = _order_item_match_maps(order)
    if not items:
        return []
    reserved = _reserved_by_line(order)
    already = set(OrderStockReservation.objects
                  .filter(order=order, consumed=False)
                  .values_list("stock_item_id", flat=True))
    rolls = (WarehouseProductItem.objects
             .filter(purchase_invoice_item__invoice=invoice)
             .exclude(pk__in=already)
             .select_related("product", "product__catalog_variant")
             .order_by("pk"))
    held = []
    for roll in rolls:
        line = _match_roll_to_order(roll, items, variant_ids, product_ids, skus)
        if line is None:
            continue
        need = _line_need(line, reserved)
        if need <= 0:
            continue
        r, _capped, err = _create_roll_reservation(order, line, roll, need, user)
        if err or r is None:
            continue
        reserved[line.pk] = reserved.get(line.pk, Decimal("0")) + r.quantity
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
    Received purchases are stock now and are left alone."""
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
    for invoice in (order.supplier_purchases.filter(status="draft")
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
                cancel_purchase_invoice(invoice.pk, user, origin="order", mirror_order=False)
                log_change(order, "field", field="purchase",
                           new=_("%(number)s cancelled — nothing left on it to buy")
                           % {"number": invoice.number})


def cancel_purchases_for_cancelled_order(order, *, user=None):
    """The order is being cancelled: stock ordered in for it is no longer
    wanted, so its draft purchases are cancelled with it. A received
    purchase is stock on the shelf and stays."""
    from accounting.views_purchase import cancel_purchase_invoice
    from .audit import log_change

    user = _auth_user(user)
    for invoice in list(order.unreceived_purchases()):
        with syncing():
            cancel_purchase_invoice(invoice.pk, user, origin="order", mirror_order=False)
        log_change(order, "field", field="purchase",
                   new=_("%(number)s cancelled with the order") % {"number": invoice.number})


def drop_purchase_lines_from_order(invoice, *, user=None):
    """The purchase was cancelled on its own page: take the lines it put
    on the customer's order off again, and cancel an order left empty.
    Returns the sentence the purchase page shows about the order, or None
    when there is nothing to say."""
    from .audit import log_change
    from .models import OrderChange
    from .views_warehouse import apply_order_status_change

    order = invoice.for_order
    if order is None or not order_is_open(order):
        return None
    number = order.order_number or order.pk
    if (order.order_status or "pending") != "pending" or \
            order.stock_reservations.filter(consumed=False).exists():
        # It has left "Open", or rolls are already held for it — the
        # packing floor owns it now. Same rule as sync_customer_order.
        return (_("Order %(number)s is already being packed, so its lines were left "
                  "as they are — check it.") % {"number": number})
    skus = plan_variant_skus(invoice.intake_plan)
    removed = 0
    with syncing():
        for item in order.items.select_related("product_variant"):
            sku = (item.product_variant.variant_sku or "").lower() if item.product_variant_id else ""
            if sku in skus:
                item.delete()
                removed += 1
        log_change(order, "field", field="purchase",
                   new=_("%(number)s cancelled — %(count)s line(s) removed")
                   % {"number": invoice.number, "count": removed})
        if order.items.exists():
            return (_("Its %(count)s line(s) were removed from order %(number)s, which "
                      "stays open with what else is on it.")
                    % {"count": removed, "number": number})
        ok, _code = apply_order_status_change(order, "cancelled", user=user)
    if not ok:
        return (_("Order %(number)s has nothing left on it but could not be cancelled "
                  "— cancel it on the order page.") % {"number": number})
    OrderChange.objects.create(
        order=order, action="field", field="cancel_reason",
        new_value=_("Purchase %(number)s cancelled") % {"number": invoice.number},
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    return (_("Order %(number)s had nothing else on it and was cancelled too.")
            % {"number": number})
