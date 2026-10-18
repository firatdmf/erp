"""Handing rolls from one book's warehouse to another's, at cost.

See models_transfer for what a transfer is. This is the one place it is
made and the one place it is taken back.

Only whole, free rolls go. A roll meters have already come off carries the
record of an order in the book it was cut in — reopening that order puts
the meters back on the roll — and a roll held for an order is promised to
that book's customer. Either would follow the roll into a ledger that never
sold anything.
"""
from collections import OrderedDict
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from .models_accounts import CurrentAccount, CurrentAccountMovement
from .models_transfer import StockTransfer, StockTransferLine


class TransferError(Exception):
    """A transfer that can't go ahead. Nothing has been written.

    `blocked` lists the rolls in the way, each {"barcode", "reason"}.
    """

    def __init__(self, message, blocked=None):
        super().__init__(message)
        self.message = message
        self.blocked = blocked or []


def receiving_account(from_book, to_book):
    """The account in `to_book` that stands for `from_book`: inter-company,
    and paired with one in that book. None when the two books keep no such
    pair — then nothing would carry the debt to the sender's side."""
    if from_book is None or to_book is None:
        return None
    return (CurrentAccount.objects
            .filter(book=to_book, type="intercompany", is_active=True,
                    mirror_account__book=from_book, mirror_since__isnull=False)
            .select_related("mirror_account", "default_currency")
            .first())


def live_transfer_of(invoice):
    """The transfer this purchase is the receiving half of, unless undone."""
    transfer = StockTransfer.objects.filter(purchase_id=getattr(invoice, "pk", invoice)).first()
    return transfer if transfer is not None and not transfer.is_undone else None


def _left(roll):
    left = roll.quantity_remaining if roll.quantity_remaining is not None else roll.quantity
    return Decimal(left or 0)


def roll_problem(roll):
    """Why this roll can't be transferred, or None when it can."""
    from .services_posting import stock_unit_cost

    if roll.status == "consumed" or _left(roll) <= 0:
        return _("used up")
    if _left(roll) != Decimal(roll.quantity or 0) or roll.movements.filter(movement_type="out").exists():
        return _("part of it has been used")
    if roll.reservations.exists():
        return _("held for an order")
    if stock_unit_cost(roll) is None:
        return _("has no cost")
    return None


def _target_product(source_wp, warehouse):
    """The same variant on the receiving shelves, made when it is not there."""
    from operating.models import WarehouseProduct

    target = WarehouseProduct.in_warehouse(warehouse, source_wp)
    if target is None:
        target = WarehouseProduct.objects.create(
            warehouse=warehouse, name=source_wp.name, sku=source_wp.sku,
            barcode=None, quantity=Decimal("0"),
            purchase_price=source_wp.purchase_price,
            purchase_currency=source_wp.purchase_currency,
            cost_usd=source_wp.cost_usd, cost_try=source_wp.cost_try,
            catalog_variant=source_wp.catalog_variant,
        )
    return target


def _settle_products(products):
    from operating.views_warehouse import _recount_wp, _resync_wp_catalog

    for wp in products:
        _recount_wp(wp)
        _resync_wp_catalog(wp)


@transaction.atomic
def transfer_stock(from_warehouse, to_warehouse, roll_ids, *, user=None, member=None,
                   date=None, note=""):
    """Transfer these rolls, at what they cost. Returns the StockTransfer.

    Raises TransferError, having written nothing.
    """
    from operating.models import WarehouseProductItem
    from operating.views_warehouse import _move_roll
    from .purchase_audit import log_purchase
    from .services_accounts import create_purchase_invoice_for_intake, invoice_currency_for
    from .services_posting import post_movement, post_stock_transfer, stock_unit_cost

    from_book = from_warehouse.accounting_book
    to_book = to_warehouse.accounting_book
    if from_warehouse.is_combined or to_warehouse.is_combined:
        raise TransferError(_("A combined warehouse is virtual — pick one of its member warehouses."))
    if from_book is None or to_book is None:
        raise TransferError(_("Both warehouses must belong to a book."))
    if from_book.pk == to_book.pk:
        raise TransferError(_("Both warehouses belong to the same book — move the stock items "
                              "between them instead."))
    account = receiving_account(from_book, to_book)
    if account is None:
        raise TransferError(
            _("%(to)s has no inter-company account paired with %(from)s, so nothing would "
              "record what it owes for the goods.") % {"to": to_book.name, "from": from_book.name})
    base = getattr(settings, "BASE_CURRENCY_CODE", "USD").upper()
    if invoice_currency_for(account) != base:
        raise TransferError(
            _("The inter-company account %(account)s is not kept in %(currency)s, the currency "
              "stock is costed in.") % {"account": account.name, "currency": base})
    date = date or timezone.localdate()
    if date > timezone.localdate():
        raise TransferError(_("A transfer can't be dated in the future."))

    roll_ids = list(dict.fromkeys(int(pk) for pk in roll_ids))
    if not roll_ids:
        raise TransferError(_("Pick at least one stock item."))
    # Locked without the joins: the product row is shared by every roll of
    # the variant, and nothing here needs it held.
    list(WarehouseProductItem.objects.select_for_update().filter(pk__in=roll_ids)
         .values_list("pk", flat=True))
    rolls = list(WarehouseProductItem.objects.filter(pk__in=roll_ids)
                 .select_related("product", "product__warehouse", "product__catalog_variant",
                                 "purchase_invoice_item")
                 .order_by("product__sku", "barcode", "pk"))
    if len(rolls) != len(roll_ids):
        raise TransferError(_("Some of these stock items no longer exist — reload the page."))

    blocked = []
    for roll in rolls:
        if roll.product.warehouse_id != from_warehouse.pk:
            reason = _("is in %(warehouse)s now") % {"warehouse": roll.product.warehouse.name}
        else:
            reason = roll_problem(roll)
        if reason:
            blocked.append({"barcode": roll.barcode or f"#{roll.pk}", "reason": str(reason)})
    if blocked:
        raise TransferError(_("Some stock items can't be transferred."), blocked)

    # One purchase line per variant and cost: a line has one price.
    targets = {}
    groups = OrderedDict()
    for roll in rolls:
        source_wp = roll.product
        if source_wp.pk not in targets:
            targets[source_wp.pk] = _target_product(source_wp, to_warehouse)
        cost = stock_unit_cost(roll)
        groups.setdefault((source_wp.pk, cost), []).append(roll)

    purchase_lines = []
    for (source_pk, cost), members in groups.items():
        target = targets[source_pk]
        variant = target.catalog_variant
        purchase_lines.append({
            "description": " — ".join(x for x in (target.name, target.sku) if x),
            "quantity": sum((_left(r) for r in members), Decimal("0")),
            "unit": target.unit,
            "unit_price": cost,
            "currency": base,
            "product": variant.product if variant is not None else None,
            "variant": variant,
        })

    invoice = create_purchase_invoice_for_intake(
        account, purchase_lines, member=member, user=user, invoice_date=date)
    movement = invoice.posted_movement
    if movement is None or not CurrentAccountMovement.objects.filter(mirror_of=movement).exists():
        raise TransferError(
            _("The debt did not reach %(book)s's side of the inter-company account.")
            % {"book": from_book.name})

    transfer = StockTransfer.objects.create(
        from_warehouse=from_warehouse, to_warehouse=to_warehouse,
        from_book=from_book, to_book=to_book, date=date, purchase=invoice,
        note=(note or "")[:300], created_by=member)

    value = Decimal("0")
    sources = {}
    items = list(invoice.items.order_by("line_no"))
    for item, ((source_pk, cost), members) in zip(items, groups.items()):
        target = targets[source_pk]
        for roll in members:
            source_wp = roll.product
            sources[source_wp.pk] = source_wp
            meters = _left(roll)
            StockTransferLine.objects.create(
                transfer=transfer, stock_item=roll, barcode=roll.barcode or "",
                sku=source_wp.sku or "", name=source_wp.name or "",
                quantity=meters, unit_cost=cost,
                source_product=source_wp, source_purchase_item=roll.purchase_invoice_item)
            value += meters * cost
            _move_roll(
                roll, target, user=user,
                reason_out=f"Transferred to {to_warehouse.name} ({to_book.name}) — {transfer.number}",
                reason_in=f"Transferred from {from_warehouse.name} ({from_book.name}) — {transfer.number}")
            roll.purchase_invoice_item = item
            roll.save(update_fields=["purchase_invoice_item"])

    transfer.value = value
    transfer.save(update_fields=["value"])
    _settle_products([*sources.values(), *targets.values()])

    log_purchase(invoice, "created", user=user,
                 new=_("transferred from %(warehouse)s (%(book)s) at cost")
                 % {"warehouse": from_warehouse.name, "book": from_book.name})
    # The purchase was posted before its rolls stood behind it, and the
    # sender's half has not been posted at all. Neither is left to a
    # receiver that swallows what goes wrong: a transfer with half its
    # ledger missing is worse than no transfer.
    post_movement(movement)
    post_stock_transfer(transfer)
    return transfer


@transaction.atomic
def undo_stock_transfer(transfer, *, user=None, member=None):
    """Take a transfer back: the rolls return to where they stood, the
    purchase is cancelled and the debt leaves both books.

    Only while every roll is still as it arrived. Raises TransferError,
    having written nothing.
    """
    from operating.views_warehouse import _move_roll
    from .purchase_audit import log_purchase
    from .services_posting import unpost

    transfer = (StockTransfer.objects.select_for_update()
                .select_related("from_warehouse", "to_warehouse", "from_book", "to_book",
                                "purchase")
                .get(pk=transfer.pk))
    if transfer.is_undone:
        raise TransferError(_("This transfer was already undone."))
    invoice = transfer.purchase
    if invoice.allocations.exists():
        raise TransferError(_("Payments are allocated to this transfer's purchase — remove "
                              "them first."))

    lines = list(transfer.lines.select_related(
        "stock_item", "stock_item__product", "stock_item__purchase_invoice_item",
        "source_product", "source_purchase_item"))
    blocked = []
    for line in lines:
        roll = line.stock_item
        if roll is None:
            reason = _("no longer exists")
        elif roll.product.warehouse_id != transfer.to_warehouse_id:
            reason = _("has left %(warehouse)s") % {"warehouse": transfer.to_warehouse.name}
        elif (roll.purchase_invoice_item is None
              or roll.purchase_invoice_item.invoice_id != invoice.pk):
            reason = _("belongs to another purchase now")
        else:
            reason = roll_problem(roll)
        if reason:
            blocked.append({"barcode": line.barcode or f"#{line.pk}", "reason": str(reason)})
    if blocked:
        raise TransferError(_("Some stock items are no longer as they arrived, so the transfer "
                              "can't be undone."), blocked)

    touched = {}
    for line in lines:
        roll = line.stock_item
        here = roll.product
        back = line.source_product
        if back is None or back.warehouse_id != transfer.from_warehouse_id:
            back = _target_product(here, transfer.from_warehouse)
        touched[here.pk] = here
        touched[back.pk] = back
        _move_roll(
            roll, back, user=user,
            reason_out=f"Transfer {transfer.number} undone — back to {transfer.from_warehouse.name}",
            reason_in=f"Transfer {transfer.number} undone — back from {transfer.to_warehouse.name}")
        roll.purchase_invoice_item = line.source_purchase_item
        roll.save(update_fields=["purchase_invoice_item"])
    _settle_products(touched.values())

    was = invoice.status
    # Deletes the purchase's movement; its mirror on the sender's account
    # goes with it, and each takes its ledger entry along.
    invoice.cancel(user=user)
    log_purchase(invoice, "status", field="status", old=was, new="cancelled", user=user)
    unpost(transfer)
    transfer.undone_at = timezone.now()
    transfer.undone_by = member
    transfer.save(update_fields=["undone_at", "undone_by"])
    return transfer
