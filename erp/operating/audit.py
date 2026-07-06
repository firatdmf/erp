# -*- coding: utf-8 -*-
"""Order audit trail — records every meaningful order change as an
OrderChange row so the order's original state and all later edits stay
visible on the detail page and the filterable changes page.

Capture is SIGNAL-based (Order + OrderItem pre/post save/delete), so it
covers every write path — create screen, edit screen, inline detail
edits, status transitions, packing completion, JSON APIs — without any
view having to remember to log. The acting user is picked up from a
request-scoped thread-local set by CurrentUserMiddleware.

Every receiver is exception-safe: auditing must never break a save.
"""
import threading

from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from .models import Order, OrderItem, OrderChange

_state = threading.local()


class CurrentUserMiddleware:
    """Stores request.user in a thread-local for the duration of the
    request so model signals can attribute changes to the acting user."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _state.user = getattr(request, "user", None)
        try:
            return self.get_response(request)
        finally:
            _state.user = None


def get_current_user():
    u = getattr(_state, "user", None)
    return u if (u is not None and getattr(u, "is_authenticated", False)) else None


def _log(order, action, field=None, item_label=None, old=None, new=None):
    """`order` may be an Order instance or a raw order id."""
    try:
        OrderChange.objects.create(
            order_id=(order.pk if isinstance(order, Order) else order),
            action=action,
            field=field,
            item_label=(item_label or "")[:255] or None,
            old_value=(str(old) if old not in (None, "") else None),
            new_value=(str(new) if new not in (None, "") else None),
            created_by=get_current_user(),
        )
    except Exception:
        pass  # never let auditing break the save


# ────────────────────────────────────────────────────────────────────
#  Order field changes
# ────────────────────────────────────────────────────────────────────
# Simple scalar fields: compared verbatim, logged one row per field.
_TRACKED_FIELDS = (
    "order_status", "carrier", "tracking_number", "notes",
    "print_header", "ettn",
    "guest_first_name", "guest_last_name", "guest_email", "guest_phone",
)
# Customer FKs: collapsed into ONE 'customer' change with resolved names.
_CUSTOMER_FIELDS = ("contact_id", "company_id", "web_client_id")


def _customer_label(order):
    try:
        if order.contact_id and order.contact:
            return f"{order.contact.name} (Contact)"
        if order.company_id and order.company:
            return f"{order.company.name} (Company)"
        if order.web_client_id and order.web_client:
            wc = order.web_client
            return f"{getattr(wc, 'name', None) or wc.username} (Web)"
    except Exception:
        pass
    g = " ".join(x for x in [order.guest_first_name, order.guest_last_name] if x)
    return f"{g} (Guest)" if g else None


@receiver(pre_save, sender=Order)
def _audit_capture_order(sender, instance, **kwargs):
    try:
        if not instance.pk:
            instance._audit_old = None
            return
        instance._audit_old = (
            Order.objects.filter(pk=instance.pk)
            .values(*(_TRACKED_FIELDS + _CUSTOMER_FIELDS))
            .first()
        )
    except Exception:
        instance._audit_old = None


@receiver(post_save, sender=Order)
def _audit_order_saved(sender, instance, created, **kwargs):
    try:
        if created:
            _log(instance, "created",
                 new=_customer_label(instance) or "—")
            return
        old = getattr(instance, "_audit_old", None)
        if not old:
            return
        for f in _TRACKED_FIELDS:
            ov = old.get(f)
            nv = getattr(instance, f, None)
            if (ov or "") != (nv or ""):
                if f == "order_status":
                    _log(instance, "status", field=f, old=ov, new=nv)
                else:
                    _log(instance, "field", field=f, old=ov, new=nv)
        if any(old.get(f) != getattr(instance, f, None) for f in _CUSTOMER_FIELDS):
            _log(instance, "field", field="customer", new=_customer_label(instance) or "—")
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────
#  Order item changes (added / removed / qty & price edits)
# ────────────────────────────────────────────────────────────────────
def _item_label(item):
    try:
        return item.display_name()
    except Exception:
        return f"item #{item.pk}"


def _fmt_qty_price(qty, price):
    q = f"{qty}" if qty is not None else "?"
    p = f"{price}" if price is not None else "?"
    return f"{q} × ${p}"


@receiver(pre_save, sender=OrderItem)
def _audit_capture_item(sender, instance, **kwargs):
    try:
        if not instance.pk:
            instance._audit_old_item = None
            return
        instance._audit_old_item = (
            OrderItem.objects.filter(pk=instance.pk)
            .values("quantity", "price", "product_id", "product_variant_id")
            .first()
        )
    except Exception:
        instance._audit_old_item = None


@receiver(post_save, sender=OrderItem)
def _audit_item_saved(sender, instance, created, **kwargs):
    try:
        if created:
            _log(instance.order_id, "item_added",
                 item_label=_item_label(instance),
                 new=_fmt_qty_price(instance.quantity, instance.price))
            return
        old = getattr(instance, "_audit_old_item", None)
        if not old:
            return
        if (old.get("product_id") != instance.product_id
                or old.get("product_variant_id") != instance.product_variant_id):
            _log(instance.order_id, "item_updated", field="product",
                 item_label=_item_label(instance),
                 new=_fmt_qty_price(instance.quantity, instance.price))
            return
        if (old.get("quantity") or 0) != (instance.quantity or 0):
            _log(instance.order_id, "item_updated", field="quantity",
                 item_label=_item_label(instance),
                 old=old.get("quantity"), new=instance.quantity)
        if (old.get("price") or 0) != (instance.price or 0):
            _log(instance.order_id, "item_updated", field="price",
                 item_label=_item_label(instance),
                 old=old.get("price"), new=instance.price)
    except Exception:
        pass


@receiver(post_delete, sender=OrderItem)
def _audit_item_deleted(sender, instance, **kwargs):
    try:
        # Order may be cascading away too — only log if it still exists.
        if not Order.objects.filter(pk=instance.order_id).exists():
            return
        _log(instance.order_id, "item_removed",
             item_label=_item_label(instance),
             old=_fmt_qty_price(instance.quantity, instance.price))
    except Exception:
        pass
