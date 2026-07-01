from decimal import Decimal

from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import (
    Order,
    OrderItem,
    OrderItemUnit,
    RawMaterialGoodItem,
    RawMaterialGoodReceipt,
)


from django.db import transaction

# from .models import generate_machine_qr_for_order


@receiver([post_save, post_delete], sender=OrderItem)
def sync_order_status(sender, instance, **kwargs):
    order = instance.order
    order.update_status_from_items()


def _adjust_catalog_stock(product_id, variant_id, delta):
    """Apply `delta` (Decimal, signed) to catalog stock.
    Positive delta = restore (e.g. order item removed / qty reduced).
    Negative delta = consume (e.g. order item created / qty raised).

    Uses F() so concurrent updates don't lose deductions. If the variant
    has its own stock field we touch that; otherwise fall back to the
    product's own quantity. Both fields are nullable — treat NULL as 0
    so existing rows without an initialised count still get decremented
    correctly."""
    if not delta:
        return
    from django.db.models import F, Value
    from django.db.models.functions import Coalesce
    from marketing.models import Product, ProductVariant

    try:
        if variant_id:
            (ProductVariant.objects
                .filter(pk=variant_id)
                .update(variant_quantity=Coalesce(F("variant_quantity"), Value(Decimal("0"))) + delta))
        elif product_id:
            (Product.objects
                .filter(pk=product_id)
                .update(quantity=Coalesce(F("quantity"), Value(Decimal("0"))) + delta))
    except Exception:
        # Catalog stock should never block the order edit — surface to
        # the stock report instead.
        pass


def _warehouse_managed_variant_ids(variant_ids):
    """Subset of the given variant ids that are stocked in a warehouse
    (i.e. some WarehouseProduct.catalog_variant points at them). For
    those variants the physical rolls are the single stock authority —
    the reservation system cuts them at ship and re-mirrors the catalog
    quantity — so the catalog-stock signals must NOT also deduct them,
    or the variant is double-counted."""
    ids = [v for v in (variant_ids or []) if v]
    if not ids:
        return set()
    try:
        from .models import WarehouseProduct
        return set(WarehouseProduct.objects
                   .filter(catalog_variant_id__in=ids)
                   .values_list("catalog_variant_id", flat=True))
    except Exception:
        return set()


@receiver(pre_save, sender=OrderItem)
def _capture_orderitem_stock_state(sender, instance, **kwargs):
    """Stash the pre-save (quantity, product_id, variant_id) on the
    instance itself so post_save can compute the delta. Only relevant
    for updates — for new rows post_save knows `created=True` and
    consumes the full quantity."""
    if not instance.pk:
        instance._stock_old_state = None
        return
    try:
        old = OrderItem.objects.only("quantity", "product_id", "product_variant_id").get(pk=instance.pk)
        instance._stock_old_state = {
            "quantity": Decimal(str(old.quantity or 0)),
            "product_id": old.product_id,
            "product_variant_id": old.product_variant_id,
        }
    except OrderItem.DoesNotExist:
        instance._stock_old_state = None


def _order_has_consumed_stock(order_id):
    """Read stock_consumed_at directly from DB so a stale Python copy
    of the Order can't make this signal silently skip a deduction."""
    if not order_id:
        return False
    try:
        return Order.objects.filter(pk=order_id).exclude(stock_consumed_at__isnull=True).exists()
    except Exception:
        return False


@receiver(post_save, sender=OrderItem)
def sync_catalog_stock_on_item_save(sender, instance, created, **kwargs):
    """Adjust catalog stock based on OrderItem changes — but ONLY when
    the parent order has already "consumed" stock (i.e. it's in a
    fulfilment status). Orders that sit in pending/preparing/packaging
    do NOT touch the catalog until they ship; that lets staff create
    orders even for products that are temporarily out of stock.

    The Order.stock_consumed_at flag marks "this order has deducted its
    items already". The Order status-transition signal below sets it
    when status crosses into STOCK_DEDUCT_STATUSES (and restores +
    clears it on the way back out)."""
    if not _order_has_consumed_stock(instance.order_id):
        return

    new_qty = Decimal(str(instance.quantity or 0))
    if created:
        # Item added to an already-shipped order: deduct immediately.
        if new_qty > 0:
            _adjust_catalog_stock(instance.product_id, instance.product_variant_id, -new_qty)
        return

    state = getattr(instance, "_stock_old_state", None)
    if not state:
        return
    old_qty = state["quantity"]
    old_pid = state["product_id"]
    old_vid = state["product_variant_id"]

    if old_pid == instance.product_id and old_vid == instance.product_variant_id:
        delta = old_qty - new_qty  # positive = restore, negative = consume
        if delta:
            _adjust_catalog_stock(instance.product_id, instance.product_variant_id, delta)
    else:
        if old_qty > 0:
            _adjust_catalog_stock(old_pid, old_vid, old_qty)
        if new_qty > 0:
            _adjust_catalog_stock(instance.product_id, instance.product_variant_id, -new_qty)


@receiver(post_delete, sender=OrderItem)
def restore_catalog_stock_on_item_delete(sender, instance, **kwargs):
    """When an OrderItem is removed — and its order had already
    consumed stock — return its quantity to the catalog. Items removed
    from pre-fulfilment orders never deducted anything so we skip."""
    if not _order_has_consumed_stock(instance.order_id):
        return
    qty = Decimal(str(instance.quantity or 0))
    if qty > 0:
        _adjust_catalog_stock(instance.product_id, instance.product_variant_id, qty)


# ────────────────────────────────────────────────────────────────────
#  Order status-transition signals — deduct/restore the whole order's
#  catalog stock when it crosses STOCK_DEDUCT_STATUSES.
# ────────────────────────────────────────────────────────────────────
@receiver(pre_save, sender=Order)
def _capture_order_old_status(sender, instance, **kwargs):
    """Stash the previous order_status on the instance so post_save
    can decide whether we're transitioning IN or OUT of a deduct state."""
    if not instance.pk:
        instance._old_status = None
        return
    try:
        old = Order.objects.only("order_status").get(pk=instance.pk)
        instance._old_status = old.order_status
    except Order.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=Order)
def email_customer_on_status_change(sender, instance, created, **kwargs):
    """Fire a transactional email when the order's order_status
    transitions into a notable state. Gated on Order.notify_customer.

    Skips the 'created' event here — that's handled at create-time in
    the view so we can guarantee the customer email is resolved off
    the freshly-saved order (signals fire before some downstream
    customer-linking steps in certain code paths)."""
    if not instance.notify_customer:
        return
    new_status = instance.order_status
    old_status = getattr(instance, "_old_status", None) if not created else None
    if not created and old_status == new_status:
        return
    # Events worth emailing about. "pending" is the initial state, not
    # a notification trigger; first email goes out at create time.
    notify_events = {
        "confirmed", "preparing", "packaging",
        "shipped", "in_transit", "out_for_delivery", "delivered",
        "cancelled", "returned",
    }
    if new_status not in notify_events:
        return
    try:
        from .order_notifications import send_order_event_email
        # Attach PDF only for the big lifecycle events. For tiny
        # status nudges the customer doesn't need the file again.
        attach_pdf = new_status in {"shipped", "delivered", "cancelled"}
        send_order_event_email(instance, new_status, attach_pdf=attach_pdf)
    except Exception as _exc:
        import traceback as _tb
        _tb.print_exc()


@receiver(post_save, sender=Order)
def sync_catalog_stock_on_order_status_change(sender, instance, created, **kwargs):
    """When the order moves INTO a fulfilment status (shipped / in
    transit / out for delivery / delivered) the catalog stock for every
    item is deducted, and stock_consumed_at is stamped. When it moves
    back OUT (cancelled, returned, or reverted to preparing), the
    deduction is reversed and the flag is cleared.

    IMPORTANT: only acts on real transitions. Any save() that leaves
    `order_status` unchanged (e.g. `update_status_from_items` writing
    the legacy `.status` field) is a no-op here. We rely on the
    DB-truth `stock_consumed_at` rather than the in-memory copy so a
    stale Python instance can't trigger a double-deduct."""
    from django.utils import timezone
    from .models import STOCK_DEDUCT_STATUSES

    new_status = instance.order_status
    old_status = getattr(instance, "_old_status", None) if not created else None

    # No transition → nothing to do. This is the common case (signals
    # firing on related-field saves that don't touch order_status).
    if old_status == new_status and not created:
        return

    # Always check the DB for the canonical stock_consumed_at — the
    # in-memory instance.stock_consumed_at can be stale because we
    # update it via .update() which bypasses the ORM cache.
    try:
        db_row = Order.objects.only("stock_consumed_at").get(pk=instance.pk)
        is_consumed = bool(db_row.stock_consumed_at)
    except Order.DoesNotExist:
        return

    should_deduct = new_status in STOCK_DEDUCT_STATUSES

    items = list(instance.items.all().only("product_id", "product_variant_id", "quantity"))
    # Variants that are stocked in a warehouse (WarehouseProduct.catalog_variant)
    # are cut from their physical ROLLS at ship time by the reservation
    # system — the catalog quantity is then re-mirrored from the warehouse.
    # Deducting them here as well would double-count them. Skip.
    managed = _warehouse_managed_variant_ids([it.product_variant_id for it in items])

    # Going INTO a deduct state and haven't deducted yet → consume.
    if should_deduct and not is_consumed:
        for it in items:
            if it.product_variant_id and it.product_variant_id in managed:
                continue
            qty = Decimal(str(it.quantity or 0))
            if qty > 0:
                _adjust_catalog_stock(it.product_id, it.product_variant_id, -qty)
        now = timezone.now()
        Order.objects.filter(pk=instance.pk).update(stock_consumed_at=now)
        instance.stock_consumed_at = now  # keep the in-memory copy honest
        return

    # Going OUT of a deduct state and already deducted → restore.
    if not should_deduct and is_consumed:
        for it in items:
            if it.product_variant_id and it.product_variant_id in managed:
                continue
            qty = Decimal(str(it.quantity or 0))
            if qty > 0:
                _adjust_catalog_stock(it.product_id, it.product_variant_id, qty)
        Order.objects.filter(pk=instance.pk).update(stock_consumed_at=None)
        instance.stock_consumed_at = None
        return


@receiver([post_save, post_delete], sender=OrderItem)
def sync_order_cari_movement(sender, instance, **kwargs):
    """Whenever an OrderItem changes (qty/price/add/remove), keep the
    linked cari movement amount in sync so the customer's balance
    reflects the latest order total in real time — regardless of which
    view did the save."""
    order = instance.order
    if not getattr(order, "cari_id", None):
        return
    try:
        from current_account.services import post_order_movement
        post_order_movement(order)
    except Exception:
        # Don't let cari sync break order edits. Errors here surface in
        # the order's "Open cari" view instead.
        pass


@receiver(post_save, sender=OrderItemUnit)
def sync_order_item_unit_status(sender, instance, **kwargs):
    print("this has been called for OrderItemUnit")
    order_item = instance.order_item
    order_item.update_status_from_units()


# update the RawMaterialGoodReceipt when adding raw material items to the receipt, so it also updates the A/P in accounting.
@receiver(post_save, sender=RawMaterialGoodItem)
@receiver(post_delete, sender=RawMaterialGoodItem)
def update_receipt_liability(sender, instance, **kwargs):
    if instance.receipt:
        instance.receipt.save()


# create liability accounts payable when we create a receipt with items.
@receiver(post_save, sender=RawMaterialGoodReceipt)
def create_or_update_liability_for_receipt(sender, instance, created, **kwargs):
    from accounting.models import LiabilityAccountsPayable

    """
    Sync LiabilityAccountsPayable whenever a RawMaterialGoodReceipt is saved.
    """
    # only process if receipt has items
    if not instance.items.exists():
        return
    
    print("your instance amount is: ", instance.amount)

    with transaction.atomic():
        liability_accounts_payable, created = (
            LiabilityAccountsPayable.objects.update_or_create(
                raw_material_good_receipt=instance,
                defaults={
                    "book": instance.book,
                    "paid":False,
                    "amount": "%.2f" % instance.amount, #2 decimal fields only.
                    "supplier": instance.supplier,
                },
            )
        )
