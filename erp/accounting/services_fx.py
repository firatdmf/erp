"""What the rate has done to a foreign-currency account.

A customer who trades in euros owes euros. The book keeps its figures in
base, so every movement on that account was crossed at the rate of its own
day: a sale at the rate when it completed, a collection at the rate when
the money arrived. Between those days the rate moves, and the base value of
what is still outstanding stops matching what it would fetch today. That
gap is a foreign-exchange gain or loss, and until someone records it the
book is carrying a receivable at a price nobody would pay for it.

Nothing here posts on its own. `fx_position` states the gap — with the
rates behind it, so it can be checked rather than believed — and
`post_fx_difference` records it only when someone decides to, as a movement
of its own type that reaches 5900 Foreign Exchange Gain/Loss and leaves
what the customer owes in their own currency exactly as it was.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext as _

CENTS = Decimal("0.01")


def _base_code():
    return getattr(settings, "BASE_CURRENCY_CODE", "USD")


def is_foreign(account):
    """Does this account trade in something other than the book's own
    currency? Only such an account can hold an FX gap."""
    own = getattr(account, "own_currency", None)
    return bool(own and own.code.upper() != _base_code().upper())


def fx_position(account, *, on_date=None):
    """What `account` is worth, as booked and as the rate stands now.

    Returns None for an account that trades in base — there is nothing for
    the rate to do to it — and otherwise a dict:

      own_balance   what the customer owes, in their currency
      base_balance  what the book currently carries that at
      rate          the rate this is being measured against
      base_at_rate  what the balance is worth at that rate
      difference    base_at_rate − base_balance: + the book is carrying it
                    too cheaply (a gain), − too dearly (a loss)
      rows          every live movement with the rate it was booked at, so
                    the figure above can be traced rather than trusted
    """
    from accounting.services import get_exchange_rate

    if not is_foreign(account):
        return None
    own = account.own_currency
    own_balance = account.own_currency_balance()
    if own_balance is None:
        # A row that cannot be converted: say so rather than publish a
        # difference built on a balance with a hole in it.
        return {"unavailable": True, "currency": own.code}

    base_balance = Decimal(str(account.cached_balance or 0))
    rate = get_exchange_rate(own.code, _base_code(), on_date=on_date)
    rate = Decimal(str(rate)) if rate else None
    if rate is None:
        return {"unavailable": True, "currency": own.code}

    base_at_rate = (own_balance * rate).quantize(CENTS, rounding=ROUND_HALF_UP)
    rows = []
    for m in (account.movements.live()
              .select_related("currency")
              .order_by("date", "id")):
        rows.append({
            "movement": m,
            "date": m.date,
            "label": m.get_movement_type_display(),
            "amount": m.amount,
            "currency": m.currency.code if m.currency_id else "",
            "rate": m.exchange_rate,
            "base": m.amount_base,
            "is_fx": m.movement_type == "fx_adjustment",
        })
    return {
        "currency": own.code,
        "symbol": own.symbol or own.code,
        "base_code": _base_code(),
        "own_balance": own_balance,
        "base_balance": base_balance,
        "rate": rate,
        "base_at_rate": base_at_rate,
        "difference": (base_at_rate - base_balance).quantize(CENTS, rounding=ROUND_HALF_UP),
        "rows": rows,
    }


@transaction.atomic
def post_fx_difference(account, *, member=None, on_date=None, position=None):
    """Record the gap `fx_position` reports, and nothing else.

    The entry is in base and of its own type, so it moves what the book
    carries the balance at (and reaches 5900 through the ordinary posting
    rules) while the customer's own-currency balance — what they actually
    owe — is untouched.

    Returns the movement, or None when there is nothing to record. Safe to
    call twice: the second call finds a gap of zero, because the first one
    closed it.
    """
    from datetime import date as _date
    from accounting.models import CurrencyCategory
    from accounting.models_accounts import CurrentAccountMovement

    pos = position or fx_position(account, on_date=on_date)
    if not pos or pos.get("unavailable"):
        return None
    difference = pos["difference"]
    if difference == Decimal("0.00"):
        return None

    base = CurrencyCategory.objects.filter(code=_base_code()).first()
    if base is None:
        return None
    when = on_date or _date.today()
    return CurrentAccountMovement.objects.create(
        current_account=account,
        book=account.book,
        date=when,
        amount=difference,
        currency=base,
        movement_type="fx_adjustment",
        # Says what was done and at which rate, because a figure in the
        # ledger that cannot be explained a year later is a figure nobody
        # trusts.
        description=_("Exchange rate difference: %(amount)s %(currency)s at %(rate)s")
        % {"amount": pos["own_balance"], "currency": pos["currency"], "rate": pos["rate"]},
        reference=f"FX-{account.code}-{when:%Y%m%d}",
        created_by=member,
    )


def book_fx_positions(book, *, on_date=None):
    """Every foreign-currency account in `book` that has anything to say,
    with the book's total gain or loss across them.

    The report answers "what has the rate done to us" in one place, which
    per-account panels cannot: a gain on one customer and a loss on another
    are the same question.
    """
    from accounting.models_accounts import CurrentAccount

    accounts = (CurrentAccount.objects.filter(book=book, is_active=True)
                .select_related("default_currency", "book")
                .order_by("name"))
    rows, total = [], Decimal("0.00")
    for account in accounts:
        if not is_foreign(account):
            continue
        pos = fx_position(account, on_date=on_date)
        if not pos:
            continue
        if not pos.get("unavailable"):
            if pos["own_balance"] == Decimal("0.00") and pos["difference"] == Decimal("0.00"):
                continue
            total += pos["difference"]
        rows.append({"account": account, "position": pos})
    return {"rows": rows, "total": total, "base_code": _base_code()}


# ---------------------------------------------------------------------------
# Realised: what a rate typed on a payment did
#
# The revaluation above is about a balance the rate moved underneath. This
# is the other way a difference arises: somebody GAVE a rate. A customer
# who owes $226.40 is refunded €201 at 1.126368 so the account closes to
# the cent; but €201 was worth $229.36 that day, and the $2.96 between the
# two is a loss the book actually took. It is not unrealised — the money
# has moved — so it is recorded the moment the payment posts, not at month
# end, and shown here so the person who typed the rate can see what it
# cost or made.
# ---------------------------------------------------------------------------

def realised_fx(payment, *, base_stated=None):
    """The gain or loss a payment's typed rate produced, or None.

    None when there is nothing to compare: no rate typed toward the book's
    base, a payment in base already, or no published rate photographed for
    the date. Otherwise a dict:

      stated_rate     the rate typed on the payment
      published_rate  the published rate for its date
      base_stated     what the payment settled on the account, in base
      base_published  what the money was worth, in base
      difference      + a gain, − a loss, for the book

    The sign follows the money. Money in worth more than it settled is a
    gain (the customer's dollars came to more than the debt they cleared);
    money out worth more than it settled is a loss (we handed over more
    than the debt we cleared).

    `base_stated` may be passed in from the ledger row the payment posted,
    so the entry built on it balances against that row to the cent.
    """
    stated, published = payment.exchange_rate, payment.published_rate
    if stated is None or published is None:
        return None
    amount = Decimal(payment.amount or 0)
    # Rounded the way the rows themselves are — CurrentAccountMovement.save
    # and CashTransactionEntry.save both quantize with the default
    # (half-even) rounding — so a rate left at the published one comes to
    # exactly the figure on the row, and not a cent either side of it.
    if base_stated is None:
        base_stated = (amount * Decimal(stated)).quantize(CENTS)
    base_published = (amount * Decimal(published)).quantize(CENTS)
    difference = (Decimal(payment.cash_sign) * (base_published - base_stated)).quantize(CENTS)
    return {
        "stated_rate": Decimal(stated),
        "published_rate": Decimal(published),
        "base_stated": Decimal(base_stated),
        "base_published": base_published,
        "difference": difference,
        "currency": payment.currency.code,
        "base_code": _base_code(),
    }


def book_realised_fx(book):
    """Every confirmed payment in `book` taken at a typed rate that differed
    from the published one, newest first, with the book's total.

    Each row's difference is already on 5900: this lists what is there and
    why, so a figure on that line can be traced to the payment and the two
    rates that made it.
    """
    from accounting.models_accounts import Payment

    payments = (Payment.objects
                .filter(book=book, status="confirmed",
                        exchange_rate__isnull=False, published_rate__isnull=False)
                .select_related("current_account", "currency")
                .order_by("-date", "-id"))
    rows, total = [], Decimal("0.00")
    for payment in payments:
        fx = realised_fx(payment)
        if not fx or fx["difference"] == Decimal("0.00"):
            continue
        rows.append({"payment": payment, "fx": fx})
        total += fx["difference"]
    return {"rows": rows, "total": total, "base_code": _base_code()}
