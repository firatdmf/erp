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
from django.utils.translation import gettext_noop

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
    # A forgiven debt is not a smaller sale — the sale happened and the
    # customer did not pay — so it goes to its own expense line, where the
    # year's total of what was let go can be read off directly.
    "write_off":        "5200",
    # A difference let go to close an account (a credit on a customer) is a
    # cost of doing business, on its own line under operating expenses; one
    # kept (a debit) is income — see DEBIT_CONTRA_BY_TYPE.
    "balance_close":    "5150",
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
    # The rate moved; the customer owes the same. Its own line, because
    # folding it into operating expenses hides the difference between
    # "we spent more" and "the lira moved" (see STANDARD_CHART 5900).
    "fx_adjustment":    "5900",
}

# The other leg when the movement is a DEBIT, for the types whose contra
# depends on which way they go. A discount we give a customer is a credit
# and a smaller sale (4000 above). One a supplier gives us is a debit — we
# owe them less — and not a sale at all, so it is income. Not 1300: by the
# time a supplier settles on a discount the goods are often already sold,
# and taking it off stock would leave the shelves valued below cost.
DEBIT_CONTRA_BY_TYPE = {
    "discount":         "4900",
    "balance_close":    "4900",
}

# The types whose other leg nobody has decided, parked rather than guessed.
#
# "adjustment" is 160 rows across the two books and it is not one thing —
# an import correction, an offset between two accounts and a write-off need
# three different contras and only a human can say which is which.
# "intercompany" is a mirror of an event in the other book, so this book has
# the value and not the reason.
#
# They used to raise instead, which was the right answer while posting was a
# batch someone ran and read the output of. It is the wrong answer now that
# every save posts: a refusal at write time would either lose the row from
# the ledger or refuse the save itself, and the first of those puts 1200
# quietly out of step with the current accounts it is supposed to summarise.
# Parked, the equation still holds and the amount stands on a line whose
# name says it is not finished.
PARKED_CONTRA_BY_TYPE = {
    "adjustment":   "1900",     # Suspense
    "intercompany": "1950",     # Inter-company Clearing
}

# Both tables together: what lines_for_movement will actually post to. A
# type in NEITHER is a type someone added to the model without deciding
# what it means, and that still raises.
ALL_CONTRA_BY_TYPE = {**CONTRA_BY_TYPE, **PARKED_CONTRA_BY_TYPE}


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

# How a Payment's money actually moved, by its method.
#
# The movement type says only that a debt was settled; the method says
# with what, and that decides the other side. A cheque in hand is not cash
# until it clears, and an offset moves no money at all — booking either
# into 1000 Cash is what would leave the cash account above every kasa and
# bank the book has.
PAYMENT_CASH_METHODS = frozenset({"cash", "bank_transfer", "credit_card"})
PAYMENT_NOTE_METHODS = frozenset({"check", "promissory_note"})
NOTES_RECEIVABLE = "1400"
NOTES_PAYABLE = "2100"
SUSPENSE = "1900"
# Where the gap between a payment's typed rate and the published one goes:
# the account moves by what the money settled, the kasa by what the money
# was worth, and this line takes the difference. See services_fx.realised_fx.
FX_GAIN_LOSS = "5900"


class NoRuleFor(ValidationError):
    """Raised for a movement type with no contra account decided yet."""


def lines_for_movement(movement):
    """The two lines this current account movement implies, balanced.

    Sign lives in one place. amount_base is positive when the account owes
    the book more, so the control leg is a debit then and a credit
    otherwise, and the contra always takes the opposite side. Written this
    way the tables above only have to name an account, never a direction,
    which is the part that is easy to get backwards.

    Returns no lines at all for a row that is not part of any balance: a
    void row, or one worth nothing.
    """
    kind = movement.movement_type
    if kind not in ALL_CONTRA_BY_TYPE:
        raise NoRuleFor(
            f"No posting rule for movement type {kind!r}. Add one to "
            f"CONTRA_BY_TYPE once it is decided what the other leg is, or "
            f"to PARKED_CONTRA_BY_TYPE to hold it in suspense until then."
        )
    contra = ALL_CONTRA_BY_TYPE[kind]
    # A void row is kept for history and counted in nothing — see
    # CurrentAccountMovementQuerySet.live(), which is what every balance
    # reads. Posting it would put 1200 above the accounts it summarises by
    # exactly the cancelled documents, and a control account that cannot be
    # reconciled is no better than no control account.
    if movement.is_void:
        return []
    amount = Decimal(movement.amount_base or 0)
    if amount == ZERO:
        return []
    if amount > ZERO:
        contra = DEBIT_CONTRA_BY_TYPE.get(kind, contra)

    # A movement written by an equity record takes that record's contra, not
    # its type's. An expense a customer paid on the book's behalf is filed as
    # an `adjustment` on their account (views.handle_expense_on_account
    # explains why), but what it is is an expense — the same 5100 a
    # cash-funded one reaches through the cash journal. Read by type alone it
    # would sit in Suspense as a decision nobody owes.
    source_model = _source_model_name(movement)
    if source_model in CASH_CONTRA_BY_SOURCE:
        contra = CASH_CONTRA_BY_SOURCE[source_model]

    cash_account = None
    payment = _payment_for(movement)
    if payment is not None:
        contra, cash_account = payment_contra(payment.method, amount < ZERO,
                                              payment.cash_account)

    memo = movement.description or movement.get_movement_type_display()
    if payment is not None:
        from .services_fx import realised_fx
        fx = realised_fx(payment, base_stated=abs(amount))
        if fx and fx["difference"] != ZERO:
            return _lines_with_realised_fx(movement, amount, contra, cash_account, memo, fx)
    if amount > ZERO:
        return [debit(CURRENT_ACCOUNT_CONTROL, amount, current_account=movement.current_account, memo=memo),
                credit(contra, amount, cash_account=cash_account, memo=memo)]
    return [credit(CURRENT_ACCOUNT_CONTROL, -amount, current_account=movement.current_account, memo=memo),
            debit(contra, -amount, cash_account=cash_account, memo=memo)]


def _lines_with_realised_fx(movement, amount, contra, cash_account, memo, fx):
    """Three lines instead of two, for a payment taken at a typed rate.

    The control leg is the movement as booked — what the person said the
    money settled. The cash (or notes, or suspense) leg is what the money
    was worth at the published rate, because a kasa holds the money, not
    the agreement. The gap lands on 5900: a credit when the book gained,
    a debit when it lost — the same side post_fx_difference's entries take,
    so the line reads one way whichever route a difference arrived by.
    """
    from django.utils.translation import gettext as _g

    gain = fx["difference"]
    worth = fx["base_published"]
    fx_memo = _g("Exchange rate difference on %(ref)s: typed %(typed)s, published %(published)s") % {
        "ref": movement.reference or memo,
        "typed": fx["stated_rate"].normalize(),
        "published": fx["published_rate"].normalize(),
    }
    fx_line = (credit(FX_GAIN_LOSS, gain, memo=fx_memo) if gain > ZERO
               else debit(FX_GAIN_LOSS, -gain, memo=fx_memo))
    if amount > ZERO:
        return [debit(CURRENT_ACCOUNT_CONTROL, amount, current_account=movement.current_account, memo=memo),
                credit(contra, worth, cash_account=cash_account, memo=memo),
                fx_line]
    return [credit(CURRENT_ACCOUNT_CONTROL, -amount, current_account=movement.current_account, memo=memo),
            debit(contra, worth, cash_account=cash_account, memo=memo),
            fx_line]


def payment_contra(method, money_in, cash_account=None):
    """(account code, cash account) for a payment made by `method`.

    `money_in` is True when the account now owes less because something
    came to the book — a collection, a supplier's refund — and False when
    something went out.

    Cash, transfers and card receipts land in 1000, tagged with the kasa or
    bank they went through. A cheque or a note received waits in 1400 until
    it is cashed, and one given in 2100 until it is paid. An offset and
    "other" say nothing about where value went, so they wait in Suspense
    until somebody does.
    """
    if method in PAYMENT_CASH_METHODS:
        return CASH_CONTROL, cash_account
    if method in PAYMENT_NOTE_METHODS:
        return (NOTES_RECEIVABLE if money_in else NOTES_PAYABLE), None
    return SUSPENSE, None


def _source_model_name(movement):
    """The lowercased model name of whatever wrote this movement, or None."""
    if not movement.source_type_id:
        return None
    from django.contrib.contenttypes.models import ContentType
    return ContentType.objects.get_for_id(movement.source_type_id).model


def _payment_for(movement):
    """The Payment behind a collection or payment movement, or None.

    Either the payment posted it (Payment.confirm sets the source), or the
    movement was typed by hand and signals_accounts made a Payment to
    match. Read from the database rather than through the generic relation:
    an edit re-saves this movement straight after changing the payment, and
    a cached copy would still carry the old method.
    """
    if movement.movement_type not in ("collection", "payment") or not movement.pk:
        return None
    from django.contrib.contenttypes.models import ContentType

    from .models_accounts import Payment

    payments = Payment.objects.select_related("cash_account")
    if (movement.source_type_id and movement.source_id and
            movement.source_type_id == ContentType.objects.get_for_model(Payment).pk):
        found = payments.filter(pk=movement.source_id).first()
        if found is not None:
            return found
    return payments.filter(posted_movement_id=movement.pk).first()


def unpost(source):
    """Remove whatever the ledger currently says about this source row.

    Returns how many entries went. Deleting rather than reversing is
    deliberate at this stage: these books are mid-migration and nothing is
    closed, so a correction should leave the ledger reading as though the
    mistake had never been typed. Once a period is closed, an edit inside
    it wants a reversal instead — see close_period, which is the point at
    which that becomes true.
    """
    from django.contrib.contenttypes.models import ContentType

    if source is None or source.pk is None:
        return 0
    ct = ContentType.objects.get_for_model(source.__class__)
    return unpost_ref(ct.pk, source.pk)


def unpost_ref(content_type_id, object_id):
    """unpost, by the pair of ids rather than by the object.

    Needed because the commonest way a source disappears is a CASCADE that
    takes its cash row with it, and by the time the row's post_delete runs
    the object it named is already gone. Keying on the ids the row still
    carries is what stops that leaving an entry behind with nothing to
    trace it to.
    """
    from .models_ledger import JournalEntry

    if not content_type_id or not object_id:
        return 0
    deleted, _ = JournalEntry.objects.filter(
        source_type_id=content_type_id, source_id=object_id).delete()
    return deleted


@transaction.atomic
def post_movement(movement, *, reference=""):
    """Make the ledger say exactly what this movement says.

    Idempotent, and that is what lets the same function serve a first post,
    an edit, a void and a re-run of the backfill. It replaces whatever was
    posted for this movement before, so calling it twice leaves one entry
    and calling it after an amount changed leaves the new amount — the
    alternative, posting only when nothing is there yet, would have let an
    edited payment keep its old figure in the ledger for ever.

    Returns the entry, or None when the movement belongs in no balance.
    """
    lines = lines_for_movement(movement)
    unpost(movement)
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
def post_opening_inventory(book, *, date, reference="", warehouse=None,
                           contra="3100"):
    """Put the stock standing in this book's warehouses on the books.

    Valued exactly as the balance sheet values it — each item at what it
    cost — so the ledger and _inventory_value cannot report two different
    inventories. Items with no cost basis are outside both figures.

    The contra is Opening Balance Equity, not a purchase: this stock was
    bought before the ledger existed and there is no payable left to
    record against it. Pass `contra="2000"` for stock that IS still owed
    for — goods received against a supplier invoice nobody has entered.

    `warehouse` posts one warehouse's stock instead of the whole book's,
    for shelves that were opened after the cutover was photographed and so
    are missing from it. The description names the warehouse, which is
    both how a reader tells the entries apart and how the caller knows not
    to post the same shelves twice.
    """
    from .services_ledger import _inventory_value

    value, unvalued_count, unvalued_qty = _inventory_value(book, warehouse)
    if value <= ZERO:
        return None, unvalued_count, unvalued_qty
    description = ("Opening inventory" if warehouse is None
                   else f"Opening inventory — {warehouse.name}")
    memo = "Stock on hand at cutover"
    entry = post_entry(
        book=book, date=date,
        description=description,
        lines=[debit("1300", value, memo=memo),
               credit(contra, value, memo=memo)],
        reference=reference,
    )
    return entry, unvalued_count, unvalued_qty


@transaction.atomic
def reclassify_payables(book, *, date, reference=""):
    """Bring Accounts Payable (2000) to the accounts that are in credit today.

    Every current account movement posts to 1200 because that is where the
    account's running balance lives. An account whose balance is NEGATIVE
    is not a receivable at all — the book owes them — so its credit belongs
    in 2000. The split was made once, at the cutover, and never again:
    customers crossing zero afterwards moved only 1200, so 2000 kept the
    cutover figure (Ergene: 764.11 against 532.47 actually owed).

    This posts the DIFFERENCE between what 2000 holds and what the accounts
    in credit add up to, so it can be run at any time, as often as liked:
    a second run posts nothing. Returns (entry or None, accounts in credit).

    It moves value between two balance-sheet accounts only. Nobody owes
    more or less afterwards, and the period's result is untouched.
    """
    from django.db.models import Sum
    from .models import Book
    from .models_accounts import CurrentAccount
    from .models_ledger import JournalLine

    # It now runs after every movement (signals_ledger), so two saves can
    # arrive together; the book row is the lock that stops both of them
    # posting the same difference.
    with transaction.atomic():
        Book.objects.select_for_update().get(pk=book.pk)
        return _reclassify_payables_locked(book, date, reference, CurrentAccount, JournalLine, Sum)


def _reclassify_payables_locked(book, date, reference, CurrentAccount, JournalLine, Sum):
    in_credit = CurrentAccount.objects.filter(book=book, cached_balance__lt=0)
    count = in_credit.count()
    owed = -(in_credit.aggregate(t=Sum("cached_balance"))["t"] or ZERO)
    held = JournalLine.objects.filter(entry__book=book, account__code="2000").aggregate(
        d=Sum("debit"), c=Sum("credit"))
    held = (held["c"] or ZERO) - (held["d"] or ZERO)
    delta = (owed - held).quantize(Decimal("0.01"))
    if delta == ZERO:
        return None, count
    memo = f"Accounts in credit: {count}, owed {owed:.2f}; payable held {held:.2f}"
    if delta > ZERO:
        lines = [debit("1200", delta, memo=memo), credit("2000", delta, memo=memo)]
    else:
        lines = [debit("2000", -delta, memo=memo), credit("1200", -delta, memo=memo)]
    entry = post_entry(
        book=book, date=date,
        description="Reclassify credit balances to accounts payable",
        lines=lines, reference=reference,
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
    """Make the ledger say exactly what this cash row says.

    Idempotent on the same terms as post_movement, and keyed on the SOURCE
    — the dividend or the expense — not on the cash row, because that is
    the event. A source that writes two cash rows would otherwise get two
    entries, each balanced on its own, and nothing would catch it.

    Returns the entry, or None when the row is worth nothing.
    """
    from django.contrib.contenttypes.models import ContentType

    model_name = ContentType.objects.get(pk=entry.content_type_id).model
    lines = lines_for_cash_entry(entry, model_name)
    source = entry.content_type.get_object_for_this_type(pk=entry.content_pk)
    unpost(source)
    if not lines:
        return None
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


# ---------------------------------------------------------------------------
# Previewing a posting before it is made
#
# The movement form shows the entry a row will write while it is being typed,
# so whoever enters it can see both sides and catch a wrong type before it
# lands — a forgiven debt picked as a discount reads, on the preview, as a
# smaller sale, which is exactly the mistake worth catching there.
# ---------------------------------------------------------------------------
def _account_meanings():
    """What each account means, in words, for the preview.

    Built per call rather than at import so it is translated into the
    language of the request that asks.
    """
    from django.utils.translation import gettext as _g
    return {
        "1000": _g("Money in a cash box or bank account."),
        "1200": _g("What this account owes the book — its balance."),
        "1300": _g("Stock bought and not yet sold."),
        "1400": _g("Cheques and notes received, not yet cashed."),
        "1500": _g("Equipment and other things the business owns for years."),
        "1900": _g("Held here until somebody decides what this really was."),
        "1950": _g("The other book's half of an inter-company movement."),
        "2000": _g("What the book owes suppliers."),
        "2100": _g("Cheques and notes given, not yet paid."),
        "3000": _g("Money the owners put into the business."),
        "3100": _g("Balances carried over from before this system — not this year's trading."),
        "3200": _g("Profit kept from earlier periods."),
        "3300": _g("Money the owners took out of the business."),
        "4000": _g("This period's sales."),
        "4900": _g("Income that is not a sale."),
        "5000": _g("What the goods sold cost when they were bought."),
        "5100": _g("Running costs: rent, wages, freight and the like."),
        "5110": _g("What winning customers costs: samples given away, fairs, catalogues."),
        "5150": _g("Small differences let go to bring a settled account to zero."),
        "5200": _g("A loss: a debt the book has given up on."),
        "5900": _g("Gains and losses from exchange rates moving."),
    }


def _describer():
    """A function turning an account code into what the previews show.

    Account names come from the chart as it stands, so a line someone has
    renamed is shown by its new name, and fall back to the standard chart
    for a line not created yet — which is every line on a fresh book.
    """
    from .models_ledger import ChartAccount
    from .services_ledger import STANDARD_CHART

    names = {code: name for code, name, _t, _c in STANDARD_CHART}
    names.update(ChartAccount.objects.values_list("code", "name"))
    meanings = _account_meanings()

    def describe(code):
        return {"code": code, "name": names.get(code, code),
                "meaning": meanings.get(code, "")}
    return describe


def payment_preview():
    """What the payment form needs to draw a payment's entry.

    The same rule payment_contra applies, laid out for a script: which
    methods go through a cash box, which wait as notes, and which types
    bring something in rather than send it out.
    """
    describe = _describer()
    return {
        "control": describe(CURRENT_ACCOUNT_CONTROL),
        "cash": describe(CASH_CONTROL),
        "notes_in": describe(NOTES_RECEIVABLE),
        "notes_out": describe(NOTES_PAYABLE),
        "suspense": describe(SUSPENSE),
        # Where a typed rate's gap to the published one goes.
        "fx": describe(FX_GAIN_LOSS),
        "cash_methods": sorted(PAYMENT_CASH_METHODS),
        "note_methods": sorted(PAYMENT_NOTE_METHODS),
        # Payment.cash_sign is +1 for these: money comes to the book.
        "money_in_types": ["collection", "refund_out"],
    }


def posting_preview():
    """The rules the movement form needs to draw an entry, as plain data."""
    describe = _describer()
    return {
        "control": describe(CURRENT_ACCOUNT_CONTROL),
        "rules": {kind: {**describe(code),
                         "parked": kind in PARKED_CONTRA_BY_TYPE,
                         **({"debit": describe(DEBIT_CONTRA_BY_TYPE[kind])}
                            if kind in DEBIT_CONTRA_BY_TYPE else {})}
                  for kind, code in ALL_CONTRA_BY_TYPE.items()},
    }


# The standard chart's names, marked so the catalogue carries them. The
# chart stores them in English and chart_of_accounts translates on the way
# out; without these makemessages would drop the Turkish as unused.
_CHART_NAMES = (
    gettext_noop("Cash and Bank"), gettext_noop("Accounts Receivable"),
    gettext_noop("Inventory"), gettext_noop("Notes Receivable"),
    gettext_noop("Fixed Assets"), gettext_noop("Suspense"),
    gettext_noop("Inter-company Clearing"), gettext_noop("Accounts Payable"),
    gettext_noop("Notes Payable"), gettext_noop("Share Capital"),
    gettext_noop("Opening Balance Equity"), gettext_noop("Retained Earnings"),
    gettext_noop("Dividends"), gettext_noop("Sales"), gettext_noop("Other Income"),
    gettext_noop("Cost of Goods Sold"), gettext_noop("Operating Expenses"),
    gettext_noop("Bad Debts Written Off"), gettext_noop("Foreign Exchange Gain/Loss"),
)


def chart_of_accounts(book):
    """Every line on the chart, what it means and what posts to it.

    "What posts here" is read off the same tables lines_for_movement and
    lines_for_cash_entry post by, so the page cannot describe a rule the
    ledger does not follow. The flows that are code rather than a table —
    stock leaving, closing a period, the payables split — are named by hand
    alongside them.
    """
    from django.utils.translation import gettext as _g

    from .models_accounts import CurrentAccountMovement
    from .models_ledger import ChartAccount
    from .services_ledger import PARENT_ACCOUNT, STANDARD_CHART, trial_balance

    labels = dict(CurrentAccountMovement.MOVEMENT_TYPES)
    feeds = {}

    def feed(code, text):
        feeds.setdefault(code, [])
        if text not in feeds[code]:
            feeds[code].append(text)

    feed(CURRENT_ACCOUNT_CONTROL, _g("Every current account movement"))
    for kind, code in ALL_CONTRA_BY_TYPE.items():
        if kind in ("legacy_ar", "legacy_ap"):
            continue
        label = str(labels.get(kind, kind))
        if kind in DEBIT_CONTRA_BY_TYPE:
            feed(code, _g("%(type)s — credit") % {"type": label})
            feed(DEBIT_CONTRA_BY_TYPE[kind], _g("%(type)s — debit") % {"type": label})
        else:
            feed(code, label)
    cash_sources = {
        "equitycapital":  _g("Capital put in"),
        "equityrevenue":  _g("Income received in cash"),
        "equityexpense":  _g("Expense paid"),
        "equitydivident": _g("Owner withdrawal"),
    }
    for model, code in CASH_CONTRA_BY_SOURCE.items():
        feed(code, cash_sources.get(model, model))
        feed(CASH_CONTROL, cash_sources.get(model, model))
    feed(NOTES_RECEIVABLE, _g("Payment received by cheque or note"))
    feed(NOTES_PAYABLE, _g("Payment made by cheque or note"))
    feed(SUSPENSE, _g("Payment by offset or other method"))
    feed(FX_GAIN_LOSS, _g("Payment at a typed rate — its gap to the published rate"))
    feed(COST_OF_GOODS_SOLD, _g("Stock leaving the warehouse"))
    feed(INVENTORY, _g("Stock leaving the warehouse"))
    feed(RETAINED_EARNINGS, _g("Closing a period"))
    feed("2000", _g("Moving credit balances out of receivables"))

    balances = {r["code"]: r["balance"] for r in trial_balance(book=book)["rows"]}
    meanings = _account_meanings()
    type_labels = dict(ChartAccount.TYPES)
    chart = {code: (name, kind, control) for code, name, kind, control in STANDARD_CHART}
    for a in ChartAccount.objects.filter(is_active=True):
        chart[a.code] = (a.name, a.type, a.is_control)

    def depth(code):
        level = 0
        while code in PARENT_ACCOUNT:
            code = PARENT_ACCOUNT[code]
            level += 1
        return level

    rows = []
    for code in sorted(chart):
        name, kind, control = chart[code]
        rows.append({
            "code": code,
            "name": _g(name),
            "type": kind,
            "type_label": type_labels.get(kind, kind),
            "normal": _g("Debit") if kind in ChartAccount.DEBIT_NORMAL else _g("Credit"),
            "is_control": control,
            "is_parked": code in PARKED_CONTRA_BY_TYPE.values(),
            "meaning": meanings.get(code, ""),
            "feeds": feeds.get(code, []),
            "balance": balances.get(code, ZERO),
            "depth": depth(code),
        })
    return rows


# ---------------------------------------------------------------------------
# Stock leaving the shelves
#
# A sale has two halves: the customer owes the money, and the goods are gone.
# The ledger only ever recorded the first, so Ergene's stock account still
# held the figure a backfill photographed at cutover while the shelves moved
# underneath it, and every sale showed its revenue against no cost at all.
#
# Keyed on StockMovement, the row the warehouse already writes for every
# change in stock: it names the item, the metres and the reason, so the
# entry can be valued at what that very roll cost rather than at an average
# nobody would recognise.
#
# Only stock going OUT posts here, plus the "in" that undoes one. Stock
# ARRIVING is deliberately left alone: intake writes a purchase invoice,
# whose current-account movement already debits 1300, and posting the stock
# row as well would count every purchase twice. Stock that arrives with no
# purchase behind it raises the shelves and not the ledger — which is the
# gap the reconciliation reports, and the next job.
# ---------------------------------------------------------------------------
COST_OF_GOODS_SOLD = "5000"
MARKETING_EXPENSES = "5110"
INVENTORY = "1300"


def stock_unit_cost(item, product=None):
    """What one unit of this stock cost, or None when nothing says.

    The same precedence the balance sheet values stock at
    (services_ledger._inventory_value), so the cost taken out on a sale is
    the cost that was carried: the item's own stamp first, because it
    cannot move, then the purchase line it arrived on, then the product's
    current cost for items received before the stamp existed.

    None means uncosted. Nothing is posted for those rather than a zero
    being invented — the balance sheet counts them the same way, and the
    unvalued count beside it is what says how much stock that is.
    """
    if item is not None:
        if item.unit_cost_base is not None:
            return Decimal(item.unit_cost_base)
        line = item.purchase_invoice_item
        if line is not None and line.unit_price is not None:
            return Decimal(line.unit_price)
        product = product or item.product
    if product is not None and product.cost_usd is not None:
        return Decimal(product.cost_usd)
    return None


def lines_for_stock_movement(movement):
    """The two lines this stock movement implies, balanced.

    Out of the warehouse: the cost of what left becomes cost of goods sold,
    or marketing expense when it left as a sample for a client.
    Back in, when it is an order being unshipped or edited, the same cost
    goes back on the shelf. Anything else — an arrival, a correction, a
    transfer between two products — returns no lines; see the note above.
    """
    kind = movement.movement_type
    is_return = kind == "in" and movement.order_id is not None
    if kind != "out" and not is_return:
        return []

    quantity = abs(Decimal(movement.quantity or 0))
    if quantity == ZERO:
        return []
    unit = stock_unit_cost(movement.stock_item, movement.product)
    if unit is None:
        return []
    value = (quantity * unit).quantize(Decimal("0.01"))
    if value == ZERO:
        return []

    memo = (movement.reason or "")[:300]
    if is_return:
        return [debit(INVENTORY, value, memo=memo),
                credit(COST_OF_GOODS_SOLD, value, memo=memo)]
    # A sample given to a client was not sold: its cost is what it took to
    # win the client, so it goes to marketing rather than into the cost of
    # the sales it sits beside.
    expense = (MARKETING_EXPENSES if getattr(movement, "purpose", "") == "sample"
               else COST_OF_GOODS_SOLD)
    return [debit(expense, value, memo=memo),
            credit(INVENTORY, value, memo=memo)]


@transaction.atomic
def post_stock_movement(movement, *, reference=""):
    """Make the ledger say what this stock movement did. Idempotent.

    Returns the entry, or None for a movement that belongs in no entry.
    """
    lines = lines_for_stock_movement(movement)
    unpost(movement)
    if not lines:
        return None
    book = movement.product.warehouse.accounting_book
    if book is None:                      # a shelf owned by nobody posts nothing
        return None
    return post_entry(
        book=book,
        date=movement.created_at.date(),
        description=(movement.reason or movement.get_movement_type_display())[:300],
        lines=lines,
        source=movement,
        reference=reference or (movement.reference or "")[:60],
    )


@transaction.atomic
def post_stock_movements(movements):
    """post_stock_movement for many movements, in a handful of queries.

    Shipping an order cuts every roll it holds, and posting each cut on its
    own took about sixteen queries — an order of 400 rolls ran past the web
    server's timeout and never shipped at all. The entries are the same
    ones, one per movement, so the ledger reads exactly as if each had been
    posted by itself; only the round trips are shared.

    The movements come from bulk_create, which sends no post_save, so this
    is their only posting. Returns the entries written.
    """
    from django.contrib.contenttypes.models import ContentType

    from .models_ledger import JournalEntry, JournalLine

    movements = [m for m in movements if m.pk is not None]
    if not movements:
        return []
    ct = ContentType.objects.get_for_model(movements[0].__class__)
    JournalEntry.objects.filter(
        source_type=ct, source_id__in=[m.pk for m in movements]).delete()

    accounts = {}
    pending = []
    for movement in movements:
        lines = lines_for_stock_movement(movement)
        if not lines:
            continue
        book = movement.product.warehouse.accounting_book
        if book is None:
            continue
        # post_entry refuses an entry whose sides disagree; checked here,
        # before anything is written, since the lines go in by bulk_create.
        if sum(l["debit"] for l in lines) != sum(l["credit"] for l in lines):
            raise ValidationError(
                f"Stock movement {movement.pk} does not balance.")
        for spec in lines:
            if spec["code"] not in accounts:
                accounts[spec["code"]] = account(spec["code"])
        pending.append((JournalEntry(
            book=book,
            date=movement.created_at.date(),
            description=(movement.reason or movement.get_movement_type_display())[:300],
            reference=(movement.reference or "")[:60],
            source_type=ct,
            source_id=movement.pk,
        ), lines))

    entries = JournalEntry.objects.bulk_create([entry for entry, _lines in pending])
    JournalLine.objects.bulk_create([
        JournalLine(
            entry=entry,
            account=accounts[spec["code"]],
            debit=spec["debit"],
            credit=spec["credit"],
            current_account=spec["current_account"],
            cash_account=spec["cash_account"],
            currency=spec["currency"],
            amount_original=spec["amount_original"],
            exchange_rate=spec["exchange_rate"],
            memo=spec["memo"],
        )
        for entry, (_entry, lines) in zip(entries, pending)
        for spec in lines
    ])
    return entries
