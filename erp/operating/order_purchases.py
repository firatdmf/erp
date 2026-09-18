"""Purchases bought FOR a customer.

A client asks for something the shelves don't have, so it is ordered in from
a supplier. The purchase form names the customer and a sale price per
variant, and saving the purchase creates the customer's order alongside it
(accounting.Invoice.for_order). This module is everything that link means:

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
                          a different one first.

A reservation is the same soft hold the order form and the packing scan
create (OrderStockReservation): nothing is cut until the order ships.
"""
from decimal import Decimal, InvalidOperation

from django.utils.translation import gettext as _

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


def put_plan_in_catalog(plan):
    """Create the catalog products and variants a draft purchase names, and
    rewrite `plan` in place to point at them — each card as an existing
    product, each variant row with the SKU it was given — so confirming the
    draft later lands its rolls on these same variants instead of minting
    new ones.

    Returns one {"product", "variant", "quantity", "sale_price"} per variant
    row that has a quantity. Raises IntakeError on the same validation
    failures a receipt would.
    """
    from .catalog_sync import CatalogSyncConflict, sync_roll_to_catalog
    from .views_warehouse import (
        IntakeError, _intake_account, _intake_main_product,
        _intake_check_lookalikes, _intake_prefix, _intake_resolve_products,
        _intake_variant_identity, _row_label,
        _intake_variants,
    )

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
            qty = sum((_decimal(t.get("qty")) for t in (v.get("tops") or [])),
                      Decimal("0"))
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
            if item["has_variants"]:
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
        order = Order(notes=_("Ordered in from %(supplier)s — purchase %(number)s")
                      % {"supplier": invoice.current_account.name,
                         "number": invoice.number})
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

    existing = {it.product_variant_id: it
                for it in order.items.select_related("product_variant")}
    previous = {s.lower() for s in previous_skus}
    wanted = set()
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
        elif item.quantity != qty or item.price != price:
            item.quantity, item.price = qty, price
            item.save(update_fields=["quantity", "price"])
    for variant_id, item in existing.items():
        sku = (item.product_variant.variant_sku or "").lower() if item.product_variant_id else ""
        if variant_id not in wanted and sku in previous:
            item.delete()

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
