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


# Events that move CASH rather than a current account. The cash journal
# names its source by model, and each of these has a contra the same way a
# movement type does.
#
# `payment` is deliberately absent, and that absence is the whole reason
# posting is keyed on the event rather than the row: a Payment writes BOTH
# a current-account movement and a cash entry, and its movement already
# carries the cash leg. Posting the cash row too would book the same
# payment twice, and each entry would balance on its own, so nothing would
# catch it.
#
# A transfer and a currency exchange are absent for a different reason:
# both of their legs are cash, so neither is a contra for the other and
# they need an entry shaped by hand.
CASH_CONTRA_BY_SOURCE = {
    "equitycapital":  "3000",   # owners put money in
    "equityrevenue":  "4900",   # income that arrived as cash, not on account
    "equityexpense":  "5100",   # operating cost paid out
    "equitydivident": "3300",   # owners took money out
}

CASH_CONTROL = "1000"


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


def lines_for_cash_entry(entry, model_name):
    """The two lines a cash-journal row implies, balanced.

    Sign again lives in one place: is_amount_positive says whether cash
    came in, so the cash leg is a debit then and a credit otherwise, and
    the contra takes the opposite side.
    """
    if model_name not in CASH_CONTRA_BY_SOURCE:
        raise NoRuleFor(
            f"No posting rule for cash source {model_name!r}. A payment is "
            f"posted through its current-account movement; a transfer and an "
            f"exchange move cash on both legs and need an entry of their own."
        )
    contra = CASH_CONTRA_BY_SOURCE[model_name]
    amount = Decimal(entry.amount_in_base_currency or 0)
    if amount == ZERO:
        return []
    # The cash row carries no description of its own; the thing that
    # created it does.
    source = entry.content_type.get_object_for_this_type(pk=entry.content_pk)
    memo = (getattr(source, "description", "") or model_name)
    if entry.is_amount_positive:
        return [debit(CASH_CONTROL, amount, cash_account=entry.cash_account, memo=memo),
                credit(contra, amount, memo=memo)]
    return [credit(CASH_CONTROL, amount, cash_account=entry.cash_account, memo=memo),
            debit(contra, amount, memo=memo)]


@transaction.atomic
def post_cash_entry(entry, *, reference=""):
    """Post one cash-journal row, or nothing. Returns the entry or None."""
    from django.contrib.contenttypes.models import ContentType

    model_name = ContentType.objects.get(pk=entry.content_type_id).model
    lines = lines_for_cash_entry(entry, model_name)
    if not lines:
        return None
    source = entry.content_type.get_object_for_this_type(pk=entry.content_pk)
    return post_entry(
        book=entry.book,
        date=entry.date,
        description=(getattr(source, "description", "") or model_name),
        lines=lines,
        source=source,
        reference=reference,
    )


# ---------------------------------------------------------------------------
# Closing the books
#
# Revenue, expenses and dividends are TEMPORARY accounts: each collects one
# period's worth and is then emptied into Retained Earnings, which is the
# permanent record of what the business has kept. Nothing emptied them, so
# they would have gone on accumulating — by the end of a second year 4000
# would hold two years of sales and 3300 two years of distributions, with
# nothing on the page able to say which year either belonged to.
#
# The balance sheet stays correct either way, because it folds revenue less
# expenses into equity as the period's result. It is the period figures
# that rot: "profit this year" quietly becomes profit since the beginning
# of time.
# ---------------------------------------------------------------------------
RETAINED_EARNINGS = "3200"

# Dividends is an equity account that behaves like a temporary one: it is a
# distribution of profit rather than a permanent part of capital, so it
# closes too.
TEMPORARY_EQUITY = ("3300",)


def _temporary_balances(book, date_to):
    """{code: net debit} for every account a close should empty.

    Net debit rather than the sign-adjusted balance on purpose: closing an
    account means posting the opposite of what sits in it, and debits minus
    credits says that directly, without having to know whether the account
    is debit- or credit-normal.
    """
    from django.db.models import Sum

    from .models_ledger import ChartAccount, JournalLine

    lines = JournalLine.objects.filter(entry__book=book)
    if date_to:
        lines = lines.filter(entry__date__lte=date_to)
    rows = (lines.values("account__code", "account__type")
            .annotate(d=Sum("debit"), c=Sum("credit")))
    out = {}
    for r in rows:
        code, type_ = r["account__code"], r["account__type"]
        temporary = (type_ in (ChartAccount.REVENUE, ChartAccount.EXPENSE)
                     or code in TEMPORARY_EQUITY)
        if not temporary:
            continue
        net = (r["d"] or ZERO) - (r["c"] or ZERO)
        if net != ZERO:
            out[code] = net
    return out


@transaction.atomic
def close_period(book, *, date_to, description=None, reference="", member=None):
    """Empty the temporary accounts into Retained Earnings.

    Returns (entry, balances), or (None, {}) when there is nothing to
    close — the answer both for a period in which nothing traded and for a
    second run over one already closed.

    Re-running needs no record of what was closed before: the entry zeroes
    each account, so a later run only ever sees what has accumulated since.

    Equity does not move. What the balance sheet counted as the period's
    result becomes part of Retained Earnings instead, which is the same
    number in a different place.
    """
    balances = _temporary_balances(book, date_to)
    if not balances:
        return None, {}

    lines, plug = [], ZERO
    for code, net in sorted(balances.items()):
        plug += net
        if net > ZERO:                      # a debit balance — credit it away
            lines.append(credit(code, net, memo="Closing entry"))
        else:
            lines.append(debit(code, -net, memo="Closing entry"))

    if plug > ZERO:                         # net debit: the period lost money
        lines.append(debit(RETAINED_EARNINGS, plug, memo="Result for the period"))
    else:
        lines.append(credit(RETAINED_EARNINGS, -plug, memo="Result for the period"))

    entry = post_entry(
        book=book, date=date_to,
        description=description or f"Close period through {date_to}",
        lines=lines, reference=reference, member=member,
    )
    return entry, balances
