"""Charges on a purchase owed to someone other than the supplier — the
carrier's delivery, mostly (models_charges.PurchaseCharge).

The purchase form posts them beside its products as

    "charges": [{"account_id": 412, "description": "Delivery",
                 "amount": "1500", "reference": "DGN-2026-118"}, ...]

and they follow the purchase's own life:

  save (draft)    save_charges()   the lines are written, nothing posts
  receive / edit  save_charges() + post_charges()
                                   each line is a payable on its account,
                                   and the total is spread over the rolls
  undo / cancel   unpost_charges() the payables go; the lines stay on the
                                   order, to post again when it is received

The spread is landed cost. Each line of the purchase takes a part of the
charges by its value, and each of its rolls carries that part per unit on
top of what the goods cost (WarehouseProductItem.charges_per_unit, inside
unit_cost_base). Meters already gone when a charge arrives took the old
cost out of stock with them; their stock movements are posted again at the
new one, so their share lands in cost of goods sold (or wherever they went)
and only the rest stays on the shelf.

A payload with no "charges" key leaves the lines as they are: the order's
own purchase panel saves the goods without them.
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

ZERO = Decimal("0")
PER_UNIT = Decimal("0.0001")


class ChargeError(Exception):
    """A charge line that can't be saved or posted, with a message for the
    person at the form. Nothing has been written."""


def parse_charges(data, supplier):
    """The charge lines `data` carries, checked, or None when it carries
    none at all (the key is absent). `supplier` is the purchase's account:
    every line is owed in its book."""
    if "charges" not in (data or {}):
        return None
    from .models_accounts import CurrentAccount

    rows = data.get("charges") or []
    if not isinstance(rows, list):
        raise ChargeError(_("Invalid data."))
    parsed = []
    for row in rows:
        if not isinstance(row, dict):
            raise ChargeError(_("Invalid data."))
        account_id = str(row.get("account_id") or "").strip()
        amount_text = str(row.get("amount") or "").strip().replace(",", ".")
        description = str(row.get("description") or "").strip()[:200]
        reference = str(row.get("reference") or "").strip()[:60]
        if not account_id and not amount_text and not description and not reference:
            continue    # a row left empty
        account = (CurrentAccount.objects.select_related("default_currency")
                   .filter(pk=int(account_id)).first() if account_id.isdigit() else None)
        if account is None:
            raise ChargeError(_("Pick who each cost is owed to."))
        if account.book_id != supplier.book_id:
            raise ChargeError(_("%(account)s keeps its books elsewhere — a cost on this "
                                "purchase is owed in its own book.") % {"account": account.name})
        try:
            amount = Decimal(amount_text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            amount = None
        if amount is None or amount <= 0:
            raise ChargeError(_("Enter what each cost came to."))
        parsed.append({"account": account, "amount": amount,
                       "description": description or "Delivery", "reference": reference})
    return parsed


def save_charges(invoice, parsed):
    """Make the purchase's charge lines `parsed` (from parse_charges), in
    place: a line keeps its row, and so its payable, where it still is.
    None leaves them alone."""
    if parsed is None:
        return
    existing = list(invoice.charges.select_related("posted_movement"))
    for position, row in enumerate(parsed):
        charge = existing[position] if position < len(existing) else None
        if charge is None:
            charge = invoice.charges.model(invoice=invoice)
        charge.position = position
        charge.current_account = row["account"]
        charge.amount = row["amount"]
        charge.description = row["description"]
        charge.reference = row["reference"]
        charge.save()
    for charge in existing[len(parsed):]:
        _delete_payable(charge)
        charge.delete()


def post_charges(invoice, *, user=None):
    """Post the purchase's charges as they now stand: a payable on each
    line's account and the total spread over the rolls. A purchase that is
    not received posts none. Must run inside the caller's transaction,
    after the rolls are attached to the purchase's lines."""
    if invoice.status != "received":
        unpost_charges(invoice)
        return
    from operating.models import WarehouseProductItem

    charges = list(invoice.charges.select_related("current_account__default_currency",
                                                  "posted_movement"))
    rolls = list(WarehouseProductItem.objects.select_for_update(of=("self",))
                 .filter(purchase_invoice_item__invoice=invoice)
                 .select_related("purchase_invoice_item"))
    if charges and not rolls:
        raise ChargeError(_("This purchase has no goods for its costs to go on."))
    total = ZERO
    for charge in charges:
        total += -_post_payable(invoice, charge, user=user).amount_base
    changed = _spread(rolls, total)
    if charges or changed:
        _post_again(invoice, charges, changed)


def unpost_charges(invoice):
    """Take the purchase's payables away, keeping its lines: the purchase is
    an order again, or cancelled. Its rolls go back to the goods' own cost
    when they are still there."""
    from operating.models import WarehouseProductItem

    charges = list(invoice.charges.select_related("posted_movement"))
    for charge in charges:
        _delete_payable(charge)
    rolls = list(WarehouseProductItem.objects.select_for_update(of=("self",))
                 .filter(purchase_invoice_item__invoice=invoice)
                 .select_related("purchase_invoice_item"))
    changed = _spread(rolls, ZERO)
    if changed:
        _post_again(invoice, [], changed)


def charged_value(invoice):
    """What the purchase's rolls carry of its charges, in base — the part
    of their value the supplier was not billed for."""
    from operating.models import WarehouseProductItem

    value = ZERO
    for qty, per_unit in (WarehouseProductItem.objects
                          .filter(purchase_invoice_item__invoice=invoice)
                          .values_list("quantity", "charges_per_unit")):
        value += Decimal(qty or 0) * Decimal(per_unit or 0)
    return value


def _post_payable(invoice, charge, *, user=None):
    """The charge's movement on its account, written or corrected in place."""
    from datetime import timedelta

    from .models_accounts import CurrentAccountMovement
    from .services_accounts import _currency_by_code, invoice_currency_for

    account = charge.current_account
    mv = charge.posted_movement
    if mv is not None and mv.current_account_id != account.pk:
        previous = mv.current_account
        mv.delete()
        previous.recompute_balance(save=True)
        mv = None
    if mv is None:
        mv = CurrentAccountMovement(
            source_type=ContentType.objects.get_for_model(charge), source_id=charge.pk,
            created_by=getattr(user, "member", None) if user else None)
    mv.current_account = account
    mv.book = invoice.book
    mv.date = invoice.posting_date
    mv.due_date = invoice.posting_date + timedelta(days=account.payment_term_days or 30)
    mv.amount = -charge.amount
    mv.amount_base = ZERO      # converted again on save, at the day's rate
    mv.currency = _currency_by_code(invoice_currency_for(account))
    mv.movement_type = "invoice_purchase"
    mv.description = f"{charge.description} — {invoice.display_number}"
    mv.reference = charge.reference or invoice.display_number
    mv.save()
    if charge.posted_movement_id != mv.pk:
        charge.posted_movement = mv
        charge.save(update_fields=["posted_movement"])
    return mv


def _delete_payable(charge):
    mv = charge.posted_movement
    if mv is None:
        return
    account = mv.current_account
    mv.delete()
    charge.posted_movement = None
    account.recompute_balance(save=True)


def _spread(rolls, total):
    """Give each roll its share of `total` (base) per unit, by the value of
    the purchase line it is on. Returns the ids of the rolls whose cost
    changed."""
    by_line = {}
    for roll in rolls:
        by_line.setdefault(roll.purchase_invoice_item_id, []).append(roll)
    measured = {line_id: sum((Decimal(r.quantity or 0) for r in line_rolls), ZERO)
                for line_id, line_rolls in by_line.items()}
    lines = {line_id: line_rolls[0].purchase_invoice_item
             for line_id, line_rolls in by_line.items() if measured[line_id] > 0}
    weights = {line_id: abs(Decimal(item.total or 0)) for line_id, item in lines.items()}
    if not any(weights.values()):
        # Nothing on it was priced: by what came in.
        weights = {line_id: measured[line_id] for line_id in lines}
    whole = sum(weights.values(), ZERO)

    changed = []
    for line_id, line_rolls in by_line.items():
        per_unit = ZERO
        if total and line_id in lines and whole:
            # Half up, as an invoice line rounds.
            per_unit = (total * weights[line_id] / whole / measured[line_id]).quantize(
                PER_UNIT, rounding=ROUND_HALF_UP)
        for roll in line_rolls:
            before = Decimal(roll.charges_per_unit or 0)
            if before == per_unit:
                continue
            roll.unit_cost_base = Decimal(roll.unit_cost_base or 0) - before + per_unit
            roll.charges_per_unit = per_unit
            roll.save(update_fields=["unit_cost_base", "charges_per_unit"])
            changed.append(roll.pk)
    return changed


def _post_again(invoice, charges, changed_roll_ids):
    """Everything whose entry reads the rolls' cost, posted again: the
    payables (their fraction of a cent), the supplier's own entry, and the
    stock that has left these rolls since they came in."""
    from operating.models import StockMovement

    from .services_posting import post_movement
    from .signals_ledger import _safely, post_bulk_stock_movements, post_purchase_again

    for charge in charges:
        if charge.posted_movement_id:
            _safely(f"purchase charge {charge.pk}", post_movement, charge.posted_movement)
    post_purchase_again(invoice)
    if changed_roll_ids:
        post_bulk_stock_movements(list(
            StockMovement.objects.filter(stock_item_id__in=changed_roll_ids)
            .select_related("stock_item__purchase_invoice_item",
                            "product__warehouse__accounting_book")))


def charge_rows_for_form(invoice):
    """The purchase's charge lines as the form's payload carries them."""
    if invoice is None:
        return []
    return [{"account_id": c.current_account_id, "account_name": c.current_account.name,
             "currency": c.currency_code, "description": c.description,
             "amount": str(c.amount), "reference": c.reference}
            for c in invoice.charges.select_related("current_account__default_currency")]
