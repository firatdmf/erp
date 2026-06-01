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


@receiver(post_save, sender=OrderItem)
def sync_catalog_stock_on_item_save(sender, instance, created, **kwargs):
    """Decrement catalog stock when an OrderItem is created, and apply
    the delta whenever quantity (or the product/variant link itself)
    changes on an existing item."""
    new_qty = Decimal(str(instance.quantity or 0))
    if created:
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
        # Same SKU — only the qty changed. delta = (new - old) consumed.
        delta = old_qty - new_qty  # positive = restore, negative = consume
        if delta:
            _adjust_catalog_stock(instance.product_id, instance.product_variant_id, delta)
    else:
        # SKU swapped on this row → restore the old, consume the new.
        if old_qty > 0:
            _adjust_catalog_stock(old_pid, old_vid, old_qty)
        if new_qty > 0:
            _adjust_catalog_stock(instance.product_id, instance.product_variant_id, -new_qty)


@receiver(post_delete, sender=OrderItem)
def restore_catalog_stock_on_item_delete(sender, instance, **kwargs):
    """When an OrderItem is removed (manually deleted or the parent
    Order is cancelled / deleted), return its quantity to the catalog."""
    qty = Decimal(str(instance.quantity or 0))
    if qty > 0:
        _adjust_catalog_stock(instance.product_id, instance.product_variant_id, qty)


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
