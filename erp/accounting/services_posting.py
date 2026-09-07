"""Turning what the subsidiary ledgers already recorded into journal entries.

Every rule here says the same thing twice: a current account movement is one half of
an event, and this names the other half. The current account ledger has always been
right about who owes what; what it never had was a contra, which is why
the equation between the ledgers drifted by $1.67M while each one stayed
internally correct.

Posting is keyed on the SOURCE EVENT, not on the row. A Payment writes a
CurrentAccountMovement and a CashTransactionEntry; a CurrentAccountTransfer writes two legs;
a currency exchange writes two cash rows. Keying on rows would post a
payment twice — once for the current account half and once for the cash half — and
each entry would balance on its own, so nothing would catch it.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .services_ledger import ZERO, account, credit, debit, post_entry

# The current account control account. Every movement has a leg here: a positive
# amount means the account owes the book more, which is a debit.
CURRENT_ACCOUNT_CONTROL = "1200"

# What the OTHER leg is, per movement type. A type with no rule raises
# rather than guessing — a movement posted to the wrong account is worse
# than one not posted at all, because it looks finished.
CONTRA_BY_TYPE = {
    # Balances carried in from the previous system. Not this year's
    # trading, so not revenue — see ChartAccount 3100.
    "opening":          "3100",
    "legacy_ar":        "3100",
    "legacy_ap":        "3100",
    # Sales. An order-attached invoice posts nothing (Invoice.issue), so
    # order_sale and invoice_sale never both describe the same goods.
    "order_sale":       "4000",
    "invoice_sale":     "4000",
    "return_sale":      "4000",
    "discount":         "4000",
    # Purchases land in stock, not in expense: the cost becomes COGS when
    # the goods leave, not when they arrive.
    "invoice_purchase": "1300",
    "return_purchase":  "1300",
    # Money moving.
    "collection":       "1000",
    "payment":          "1000",
    "advance_in":       "1000",
    "advance_out":      "1000",
    # Notes and bills.
    "check_in":         "1400",
    "check_out":        "2100",
    "interest":         "4900",
    # "adjustment" is deliberately absent. 103 of them sit on Laleli and
    # they are not one thing — an import correction, an offset between two
    # accounts and a write-off need three different contras and only a
    # human can say which is which.
}


class NoRuleFor(ValidationError):
    """Raised for a movement type with no contra account decided yet."""


def lines_for_movement(movement):
    """The two lines this current account movement implies, balanced.

    Sign lives in one place. amount_base is positive when the account owes
    the book more, so the control leg is a debit then and a credit
    otherwise, and the contra always takes the opposite side. Written this
    way the table above only has to name an account, never a direction,
    which is the part that is easy to get backwards.
    """
    kind = movement.movement_type
    if kind not in CONTRA_BY_TYPE:
        raise NoRuleFor(
            f"No posting rule for movement type {kind!r}. Add one to "
            f"CONTRA_BY_TYPE once it is decided what the other leg is."
        )
    contra = CONTRA_BY_TYPE[kind]
    amount = Decimal(movement.amount_base or 0)
    if amount == ZERO:
        return []

    memo = movement.description or movement.get_movement_type_display()
    if amount > ZERO:
        return [debit(CURRENT_ACCOUNT_CONTROL, amount, current_account=movement.current_account, memo=memo),
                credit(contra, amount, memo=memo)]
    return [credit(CURRENT_ACCOUNT_CONTROL, -amount, current_account=movement.current_account, memo=memo),
            debit(contra, -amount, memo=memo)]


@transaction.atomic
def post_movement(movement, *, reference=""):
    """Post one current account movement, or nothing. Returns the entry or None."""
    lines = lines_for_movement(movement)
    if not lines:
        return None
    return post_entry(
        book=movement.book,
        date=movement.date,
        description=movement.description or movement.get_movement_type_display(),
        lines=lines,
        source=movement,
        reference=reference or movement.reference or "",
    )


@transaction.atomic
def post_opening_inventory(book, *, date, reference=""):
    """Put the stock standing in this book's warehouses on the books.

    Valued exactly as the balance sheet values it — each item at what it
    cost — so the ledger and _inventory_value cannot report two different
    inventories. Items with no cost basis are outside both figures.

    The contra is Opening Balance Equity, not a purchase: this stock was
    bought before the ledger existed and there is no payable left to
    record against it.
    """
    from .services_ledger import _inventory_value

    value, unvalued_count, unvalued_qty = _inventory_value(book)
    if value <= ZERO:
        return None, unvalued_count, unvalued_qty
    entry = post_entry(
        book=book, date=date,
        description="Opening inventory",
        lines=[debit("1300", value, memo="Stock on hand at cutover"),
               credit("3100", value, memo="Stock on hand at cutover")],
        reference=reference,
    )
    return entry, unvalued_count, unvalued_qty


@transaction.atomic
def reclassify_payables(book, *, date, reference=""):
    """Move the accounts that are in credit from receivable to payable.

    Every current account movement posts to 1200 because that is where the account's
    running balance lives. An account whose balance ends up NEGATIVE is
    not a receivable at all — the book owes them — and a balance sheet
    that nets the two together understates both sides. One entry at the
    end moves the credit balances across, which is how a subsidiary
    ledger is reconciled to its control accounts anywhere else.
    """
    from .models_accounts import CurrentAccount

    total = -(CurrentAccount.objects.filter(book=book, cached_balance__lt=0)
              .aggregate(t=__import__("django.db.models", fromlist=["Sum"])
                         .Sum("cached_balance"))["t"] or ZERO)
    if total <= ZERO:
        return None, 0
    count = CurrentAccount.objects.filter(book=book, cached_balance__lt=0).count()
    entry = post_entry(
        book=book, date=date,
        description="Reclassify credit balances to accounts payable",
        lines=[debit("1200", total, memo="Credit balances out of receivable"),
               credit("2000", total, memo="Credit balances into payable")],
        reference=reference,
    )
    return entry, count
