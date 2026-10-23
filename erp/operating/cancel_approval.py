"""A cancel that would cancel supplier purchases waits for a book admin.

An order bought for through a purchase that has not arrived yet takes that
purchase with it when it goes: cancelling the order, deleting it, or
removing the lines that leave the purchase with nothing to buy all cancel
the purchase (order_purchases). That is a decision about money owed to a
supplier, so it is the book admins' to make. Anyone else who asks gets an
OrderCancelRequest instead, and the order stands frozen — no editing,
packing or status change — until an admin approves it (the change is then
made in the admin's name) or rejects it.

A book admin is a member with the admin grant (erp.ownership.is_admin)
who works in every book the order touches — both halves' books for a
split order — or a superuser or staff member.
"""
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import OrderCancelRequest, OrderChange, OrderItem, OrderStockReservation
from .split_orders import order_book, split_halves


class ApprovalError(Exception):
    """The request could not be made or decided; the message says why."""


def _user(actor):
    """A User, from either a User or a Member."""
    if actor is None or hasattr(actor, "is_authenticated"):
        return actor
    return getattr(actor, "user", None)


def is_book_admin(actor, order):
    from accounting.services_accounts import member_books
    from erp.ownership import is_admin

    user = _user(actor)
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    if not is_admin(user):
        return False
    member = getattr(user, "member", None)
    allowed = set(member_books(member).values_list("pk", flat=True))
    books = {getattr(order_book(half), "pk", None) for half in split_halves(order)}
    return None not in books and books <= allowed


def purchases_waiting(order):
    """The purchases still on their way in for this order, or for any half
    of it when it is split — what cancelling it would cancel."""
    from accounting.models_accounts import Invoice
    return Invoice.objects.filter(
        type="purchase", status="ordered",
        for_order__in=[half.pk for half in split_halves(order)])


def needs_approval(actor, order):
    return purchases_waiting(order).exists() and not is_book_admin(actor, order)


def pending_request(order):
    """The open request on this order or on another half of it, or None."""
    return (OrderCancelRequest.objects
            .filter(order__in=[half.pk for half in split_halves(order)], status="pending")
            .select_related("requested_by").first())


def frozen_error(order):
    """Why the order can't be changed right now, or None."""
    if pending_request(order) is not None:
        from .views_warehouse import CANCEL_PENDING_MSG
        return str(CANCEL_PENDING_MSG)
    return None


def purchases_emptied_by(order, items):
    """The waiting purchases these lines are the last of: removing them
    would leave each with nothing to buy, so it would be cancelled."""
    from .order_purchases import _plan_has_rows

    skus = {(it.product_variant.variant_sku or "").strip().lower()
            for it in items if it.product_variant_id}
    skus.discard("")
    if not skus:
        return []
    emptied = []
    for invoice in order.supplier_purchases.filter(status="ordered"):
        plan = invoice.intake_plan or {}
        names = {(v.get("sku") or "").strip().lower()
                 for p in plan.get("products") or [] for v in p.get("variants") or []}
        if not names & skus:
            continue
        left = {"products": [
            {"variants": [v for v in p.get("variants") or []
                          if (v.get("sku") or "").strip().lower() not in skus]}
            for p in plan.get("products") or []]}
        if not _plan_has_rows(left):
            emptied.append(invoice)
    return emptied


def held_lines(order, item_ids, actor):
    """Of the lines about to be removed, the ones that need a book admin:
    those naming a variant on a purchase the removal would leave empty.
    Returns (held item ids, the purchases emptied) — both empty for a
    book admin, whose removal simply goes ahead."""
    if is_book_admin(actor, order):
        return [], []
    items = list(order.items.filter(pk__in=[int(pk) for pk in item_ids])
                 .select_related("product_variant"))
    emptied = purchases_emptied_by(order, items)
    if not emptied:
        return [], []
    planned = {(v.get("sku") or "").strip().lower()
               for invoice in emptied
               for p in (invoice.intake_plan or {}).get("products") or []
               for v in p.get("variants") or []}
    held = [it.pk for it in items if it.product_variant_id
            and (it.product_variant.variant_sku or "").strip().lower() in planned]
    return held, emptied


def _book_admin_members(order):
    from authentication.models import Member

    members = (Member.objects.filter(user__is_active=True)
               .select_related("user").distinct())
    return [m for m in members if m.user_id and is_book_admin(m.user, order)]


def _notify(members, order, title, message):
    """`order` is None once it has been deleted: the notice then opens
    the order list."""
    from notifications.models import Notification
    link = (reverse("operating:order_detail", args=[order.pk]) if order is not None
            else reverse("operating:order_list"))
    for member in members:
        try:
            Notification.create_notification(
                recipient=member, notification_type="order_cancel_request",
                title=title, message=message, link=link, icon="fa-ban",
                content_object=order)
        except Exception:
            pass        # a notice that can't be sent must not lose the request


def _log(order, field, value, user):
    OrderChange.objects.create(order=order, action="field", field=field,
                               new_value=value, created_by=user)


def request_approval(order, actor, action, *, reason="", item_ids=None):
    """Ask the book admins. Returns the OrderCancelRequest."""
    user = _user(actor)
    reason = (reason or "").strip()
    if action == "cancel" and not reason:
        raise ApprovalError(_("Enter a reason to cancel the order."))
    with transaction.atomic():
        if pending_request(order) is not None:
            raise ApprovalError(_("A cancellation of this order is already waiting for approval."))
        req = OrderCancelRequest.objects.create(
            order=order, action=action, reason=reason,
            item_ids=list(item_ids or []), requested_by=user)
        numbers = ", ".join(purchases_waiting(order).values_list("number", flat=True))
        _log(order, "cancel_request",
             "%s — %s" % (req.get_action_display(), reason) if reason else req.get_action_display(),
             user)
    who = (user.get_full_name() or user.username) if user else _("Someone")
    _notify(_book_admin_members(order), order,
            _("Approval needed: %(action)s %(order)s")
            % {"action": req.get_action_display().lower(), "order": order.order_number or order.pk},
            _("%(who)s asks. It cancels purchases %(numbers)s. %(reason)s")
            % {"who": who, "numbers": numbers, "reason": reason})
    return req


def remove_items(order, item_ids):
    """Take these lines off the order, releasing what was held for them —
    a SET_NULL would otherwise leave their rolls reserved forever."""
    OrderStockReservation.objects.filter(
        order_item__pk__in=item_ids, order=order, consumed=False).delete()
    OrderItem.objects.filter(pk__in=item_ids, order=order).delete()
    if order.current_account_id:
        from accounting.services_accounts import post_order_movement
        post_order_movement(order)


def delete_order(order, actor):
    """Delete an order and cancel what is still on its way in for it.
    Returns the numbers of the purchases cancelled."""
    from .order_purchases import cancel_purchases_for_cancelled_order
    cancelled = cancel_purchases_for_cancelled_order(order, user=_user(actor), deleted=True)
    order.delete()
    return cancelled


def approve(req, actor):
    """Make the change the request asked for, in the approver's name."""
    user = _user(actor)
    order = req.order
    if req.status != "pending":
        raise ApprovalError(_("This request has already been decided."))
    if not is_book_admin(user, order):
        raise ApprovalError(_("Only an admin of this order's book can decide this."))
    label = order.order_number or order.pk
    with transaction.atomic():
        req.status = "approved"
        req.decided_by = user
        req.decided_at = timezone.now()
        req.save(update_fields=["status", "decided_by", "decided_at"])
        if req.action == "delete":
            delete_order(order, user)
            order = None
        else:
            _log(order, "cancel_request", _("Approved"), user)
            if req.action == "cancel":
                from .views_warehouse import apply_order_status_change
                ok, code = apply_order_status_change(order, "cancelled", user=user)
                if not ok:
                    raise ApprovalError(_("The order could not be cancelled: %(code)s")
                                        % {"code": code})
                _log(order, "cancel_reason", req.reason, user)
            else:
                remove_items(order, req.item_ids)
    _tell_requester(req, order, label, _("Approved"))
    return req


def reject(req, actor, note=""):
    user = _user(actor)
    order = req.order
    if req.status != "pending":
        raise ApprovalError(_("This request has already been decided."))
    if not is_book_admin(user, order):
        raise ApprovalError(_("Only an admin of this order's book can decide this."))
    req.status = "rejected"
    req.decided_by = user
    req.decided_at = timezone.now()
    req.decision_note = (note or "").strip()
    req.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])
    _log(order, "cancel_request",
         "%s — %s" % (_("Rejected"), req.decision_note) if req.decision_note else _("Rejected"),
         user)
    _tell_requester(req, order, order.order_number or order.pk, _("Rejected"))
    return req


def _tell_requester(req, order, label, outcome):
    member = getattr(req.requested_by, "member", None) if req.requested_by_id else None
    if member is None:
        return
    _notify([member], order,
            _("%(outcome)s: %(action)s %(order)s")
            % {"outcome": outcome, "action": req.get_action_display().lower(), "order": label},
            req.decision_note)
