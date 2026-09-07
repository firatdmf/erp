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


# Catalog stock is NOT mirrored into the catalog any more, so the receivers
# that used to do it are gone: _adjust_catalog_stock, the OrderItem pre/post
# save + delete pair, and sync_catalog_stock_on_order_status_change.
#
# They existed only to keep Product.quantity / ProductVariant.variant_quantity
# in step as orders shipped and un-shipped, and those columns no longer exist
# — a variant's stock is read from the WarehouseProduct rows behind it (see
# marketing.models.ProductVariant.live_quantity). Physical stock is untouched
# by this: rolls are still cut from the shelf at ship time by
# OrderStockReservation, which is what actually moves metres.
#
# Order.stock_consumed_at was written and read only by that machinery. It is
# now vestigial — nothing sets it and nothing reads it.

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


@receiver([post_save, post_delete], sender=OrderItem)
def sync_order_current_account_movement(sender, instance, **kwargs):
    """Whenever an OrderItem changes (qty/price/add/remove), keep the
    linked current account movement AND the order's live invoice in sync so the
    customer's balance and their invoice both reflect the latest order
    total in real time — regardless of which view did the save.

    The invoice half matters because it used to be cut once and never
    revisited: an edit moved the current account but left the invoice on the old
    figure, so the two documents disagreed with nothing flagging it."""
    order = instance.order
    if not getattr(order, "current_account_id", None):
        return
    try:
        from accounting.services_accounts import (
            post_order_movement, sync_invoice_for_order,
        )
        post_order_movement(order)
        sync_invoice_for_order(order)
    except Exception:
        # Don't let current account sync break order edits. Errors here surface in
        # the order's "Open current account" view instead.
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


# A raw-material receipt used to sync a LiabilityAccountsPayable row here.
# That table is gone, and nothing replaces the receiver: a purchase now
# posts its debt to a current account through the intake panel, which
# writes a purchase Invoice against the current account the operator picks (see
# accounting.views_purchase.GoodsReceipt). Reviving this would post the
# same debt twice.


# Order audit trail — signal receivers live in audit.py; importing
# here guarantees they are registered alongside the other signals.
from . import audit  # noqa: E402,F401
