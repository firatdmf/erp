"""Posting to the general ledger, and reading statements back out of it.

`post_entry` is the only supported way to write a journal entry. It takes
the lines, writes them, and refuses the lot if the debits and credits do
not agree — inside one transaction, so a refusal leaves nothing behind.
Callers therefore cannot half-post: an event either lands balanced or does
not land.

That is the whole point of the exercise. The subsidiary ledgers each stayed
correct about their own subject while the equation between them drifted by
$1.67M, because nothing ever had to agree with anything else at write time.
Here it does.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from .models_ledger import ChartAccount, JournalEntry, JournalLine

ZERO = Decimal("0.00")


# ---------------------------------------------------------------------------
# The standard chart
#
# Deliberately short. A chart with an account for everything is a chart
# nobody codes to correctly; these are the lines the business actually has,
# and the subsidiary ledgers carry the detail underneath the control
# accounts. Add to it when a real transaction has nowhere to go, not in
# advance.
# ---------------------------------------------------------------------------
STANDARD_CHART = [
    # code,  name,                         type,       is_control
    ("1000", "Cash and Bank",              "asset",     True),
    ("1200", "Accounts Receivable",        "asset",     True),
    ("1300", "Inventory",                  "asset",     True),
    ("1400", "Notes Receivable",           "asset",     True),
    ("1500", "Fixed Assets",               "asset",     False),
    # Two holding lines, both of which are supposed to end up empty.
    #
    # Suspense takes the contra of a movement whose other leg nobody has
    # decided yet — the 160 adjustments, which are an import correction, an
    # offset between two accounts and a write-off all filed under one word.
    # Parking them keeps 1200 reconcilable against the current accounts,
    # which is the whole job of a control account; refusing them instead
    # left the ledger tidy and silently short by their value.
    #
    # Inter-company clearing takes the contra of a mirror row. A mirror is
    # the other book's half of an event that happened elsewhere, so this
    # book knows the value but not the reason. Across a paired book the two
    # clearing balances are equal and opposite, which is a check nothing
    # else performs.
    #
    # Both are assets by declaration only, so that they sort with the other
    # 1000s; either can hold a credit balance and read as negative, which is
    # the honest way for an unclassified amount to look.
    ("1900", "Suspense",                   "asset",     False),
    ("1950", "Inter-company Clearing",     "asset",     False),
    ("2000", "Accounts Payable",           "liability", True),
    ("2100", "Notes Payable",              "liability", True),
    ("3000", "Share Capital",              "equity",    False),
    # The contra for balances carried in from the previous system. Every
    # opening receivable and payable needs a credit somewhere, and this is
    # where it belongs — not spread across revenue, which would report a
    # prior year's trading as this year's.
    ("3100", "Opening Balance Equity",     "equity",    False),
    ("3200", "Retained Earnings",          "equity",    False),
    ("3300", "Dividends",                  "equity",    False),
    ("4000", "Sales",                      "revenue",   False),
    ("4900", "Other Income",               "revenue",   False),
    ("5000", "Cost of Goods Sold",         "expense",   False),
    ("5100", "Operating Expenses",         "expense",   False),
    # Debts the book has given up on. Apart from operating expenses so that
    # "how much did we forgive this year" is one line, not a search.
    ("5200", "Bad Debts Written Off",      "expense",   False),
    # FX belongs on its own line. Folded into operating expenses it hides
    # the difference between "we spent more" and "the lira moved".
    ("5900", "Foreign Exchange Gain/Loss", "expense",   False),
]


def ensure_chart():
    """Create any missing standard accounts. Idempotent.

    Existing accounts are left exactly as they are — a name someone has
    edited is theirs, not something a deploy should quietly rewrite.
    """
    created = []
    for code, name, type_, is_control in STANDARD_CHART:
        _, made = ChartAccount.objects.get_or_create(
            code=code,
            defaults={"name": name, "type": type_, "is_control": is_control},
        )
        if made:
            created.append(code)
    return created


# The standard chart, keyed by code, for the lookup below.
_STANDARD_BY_CODE = {row[0]: row for row in STANDARD_CHART}


def account(code):
    """The chart account with this code, creating it if it is a standard one.

    Creating on demand, rather than insisting somebody ran a seed command
    first, because of what the alternative costs now that posting is live.
    A missing account used to mean a batch run printed an error somebody
    read; it now means every save quietly fails to post, and the ledger
    drifts from the accounts it summarises without anything on a page
    saying so. The chart is a constant of the system, not user data, so
    there is nothing to lose by materialising a line of it the moment it is
    first needed.

    A code that is NOT in the standard chart still raises. That is a
    posting rule naming an account nobody defined — a typo or a half-made
    decision — and inventing an account to match would turn a loud mistake
    into a silent one.
    """
    try:
        return ChartAccount.objects.get(code=code)
    except ChartAccount.DoesNotExist:
        pass
    if code not in _STANDARD_BY_CODE:
        raise ValidationError(
            f"No chart account {code!r}, and it is not part of the standard "
            f"chart. Either the posting rule naming it has a typo, or the "
            f"account needs adding to STANDARD_CHART."
        )
    _code, name, type_, is_control = _STANDARD_BY_CODE[code]
    obj, _made = ChartAccount.objects.get_or_create(
        code=code, defaults={"name": name, "type": type_,
                             "is_control": is_control})
    return obj


def debit(code, amount, **kwargs):
    """A debit line, for handing to post_entry."""
    return _line(code, debit=amount, **kwargs)


def credit(code, amount, **kwargs):
    """A credit line, for handing to post_entry."""
    return _line(code, credit=amount, **kwargs)


def _line(code, debit=ZERO, credit=ZERO, *, current_account=None, cash_account=None,
          currency=None, amount_original=None, exchange_rate=None, memo=""):
    return {
        "code": code,
        "debit": Decimal(debit or 0).quantize(Decimal("0.01")),
        "credit": Decimal(credit or 0).quantize(Decimal("0.01")),
        "current_account": current_account,
        "cash_account": cash_account,
        "currency": currency,
        "amount_original": amount_original,
        "exchange_rate": exchange_rate,
        "memo": memo,
    }


@transaction.atomic
def post_entry(*, book, date, description, lines, source=None, reference="",
               member=None):
    """Write one balanced journal entry, or write nothing.

    `lines` are the dicts built by debit()/credit(). Amounts are BASE
    currency; pass the entered figures alongside in `currency`,
    `amount_original` and `exchange_rate` when they differ, so an FX
    difference stays explainable.

    Raises ValidationError — inside the atomic block, so the entry and its
    lines roll back together — when the two sides disagree or when there
    are no lines.
    """
    if not lines:
        raise ValidationError("A journal entry needs lines.")

    entry = JournalEntry.objects.create(
        book=book,
        date=date,
        description=description,
        reference=reference,
        source_type=(
            _content_type(source) if source is not None else None
        ),
        source_id=getattr(source, "pk", None) if source is not None else None,
        created_by=member,
    )

    for spec in lines:
        JournalLine.objects.create(
            entry=entry,
            account=account(spec["code"]),
            debit=spec["debit"],
            credit=spec["credit"],
            current_account=spec["current_account"],
            cash_account=spec["cash_account"],
            currency=spec["currency"],
            amount_original=spec["amount_original"],
            exchange_rate=spec["exchange_rate"],
            memo=spec["memo"],
        )

    # After the lines, before the transaction closes. An unbalanced entry
    # never reaches the database in a committed state.
    entry.assert_balanced()
    return entry


def _content_type(obj):
    from django.contrib.contenttypes.models import ContentType
    return ContentType.objects.get_for_model(obj.__class__)


# ---------------------------------------------------------------------------
# Reading it back
# ---------------------------------------------------------------------------
def trial_balance(book=None, date_to=None):
    """Every account with a balance, and the two column totals.

    This is a REAL trial balance — the sum of all debits against the sum of
    all credits, which is the check that the ledger is internally sound.
    (The report currently called "Trial Balance" in this app is a per-current account
    opening/movement/closing listing, and it sums entered amounts across
    currencies, so on Laleli it reports 301,818.20 for a position of
    347,539.92.)
    """
    lines = JournalLine.objects.select_related("account")
    if book is not None:
        lines = lines.filter(entry__book=book)
    if date_to is not None:
        lines = lines.filter(entry__date__lte=date_to)

    rows = (
        lines.values("account__code", "account__name", "account__type")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
        .order_by("account__code")
    )
    out, total_debit, total_credit = [], ZERO, ZERO
    for r in rows:
        d, c = r["debit"] or ZERO, r["credit"] or ZERO
        total_debit += d
        total_credit += c
        debit_normal = r["account__type"] in ChartAccount.DEBIT_NORMAL
        out.append({
            "code": r["account__code"],
            "name": r["account__name"],
            "type": r["account__type"],
            "debit": d,
            "credit": c,
            "balance": (d - c) if debit_normal else (c - d),
        })
    return {
        "rows": out,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "difference": total_debit - total_credit,
        "balanced": total_debit == total_credit,
    }


def balance_sheet(book, date_to=None):
    """Assets, liabilities and equity for one book, out of the ledger.

    Revenue and expenses are folded into equity as the period's result —
    a balance sheet drawn before the books are closed still has to include
    them, or it will not balance for the honest reason that the year's
    profit has nowhere to sit yet.

    `difference` is zero whenever the ledger is sound, because every entry
    balanced on the way in. It is returned anyway rather than asserted: a
    statement that quietly assumes its own correctness is how the current
    situation went unnoticed.
    """
    tb = trial_balance(book=book, date_to=date_to)
    groups = {t: [] for t, _label in ChartAccount.TYPES}
    for row in tb["rows"]:
        groups[row["type"]].append(row)

    def total(kind):
        return sum((r["balance"] for r in groups[kind]), ZERO)

    assets = total(ChartAccount.ASSET)
    liabilities = total(ChartAccount.LIABILITY)
    equity_accounts = total(ChartAccount.EQUITY)
    revenue = total(ChartAccount.REVENUE)
    expenses = total(ChartAccount.EXPENSE)
    result = revenue - expenses
    equity = equity_accounts + result

    return {
        "book": book,
        "date_to": date_to,
        "groups": groups,
        "assets": assets,
        "liabilities": liabilities,
        "equity_accounts": equity_accounts,
        "revenue": revenue,
        "expenses": expenses,
        "result": result,
        "equity": equity,
        # Computed here, not with the template's `add` filter: that
        # coerces through int() and drops the cents, which rendered a
        # balanced 329,496.42 as 329,496.00 and made a sound statement
        # look broken.
        "liabilities_plus_equity": liabilities + equity,
        "difference": assets - (liabilities + equity),
        "balanced": assets == liabilities + equity,
        "trial_balance": tb,
    }


# ---------------------------------------------------------------------------
# The same equation, computed the OLD way
#
# The general ledger will be right by construction, but it starts empty, and
# it stays partly empty until every posting path is wired and history is
# backfilled. Meanwhile the money is all still in the subsidiary ledgers, and
# the only honest way to show progress is to put the two side by side: what
# the ledger says, and what the subsidiary ledgers say. When they agree, the
# migration is done.
#
# This half does not balance and is not supposed to pretend otherwise. What
# it does instead is account for its own residual exactly:
#
#     residual = net current account position
#              + cash that moved for a non-equity reason
#              + inventory held
#              + fixed assets held
#
# which is an identity, not an estimate: every current account movement lacks an equity
# contra, and every payment/exchange/transfer moves cash without being income
# or capital. Nothing is left over to hand-wave about.
# ---------------------------------------------------------------------------
_EQUITY_SOURCES = ("equitycapital", "equityrevenue", "equityexpense",
                   "equitydivident")


def _signed_cash():
    from django.db.models import Case, DecimalField, F, Value, When
    from django.db.models.functions import Coalesce
    return Case(
        When(is_amount_positive=True,
             then=Coalesce(F("amount_in_base_currency"), Value(ZERO))),
        default=-Coalesce(F("amount_in_base_currency"), Value(ZERO)),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )


def subsidiary_equation(book):
    """Assets, liabilities and equity as the subsidiary ledgers have them.

    Every figure is base currency. Inventory is the stock standing in the
    warehouses this book owns, valued at the purchase-invoice line where
    there is one and the product's cost_usd otherwise; the rolls with
    neither are counted beside the value, so an unvalued asset cannot
    quietly read as a zero one.
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Count, F, DecimalField, ExpressionWrapper, Q

    from .models import AssetFixedAsset, CashTransactionEntry
    from .models_accounts import CurrentAccount, CurrentAccountMovement

    entries = CashTransactionEntry.objects.filter(book=book)
    signed = _signed_cash()

    cash = entries.aggregate(t=Sum(signed))["t"] or ZERO

    current_account = CurrentAccount.objects.filter(book=book)
    receivable = current_account.filter(cached_balance__gt=0).aggregate(
        t=Sum("cached_balance"))["t"] or ZERO
    payable = -(current_account.filter(cached_balance__lt=0).aggregate(
        t=Sum("cached_balance"))["t"] or ZERO)

    inventory, unvalued_rolls, unvalued_metres = _inventory_value(book)
    fixed = AssetFixedAsset.objects.filter(book=book).aggregate(
        t=Sum("value"))["t"] or ZERO

    # Equity is exactly the cash entries whose source is an equity model.
    by_source = {}
    for ct_id in entries.values_list("content_type", flat=True).distinct():
        model = ContentType.objects.get(pk=ct_id).model
        by_source[model] = entries.filter(content_type_id=ct_id).aggregate(
            t=Sum(signed))["t"] or ZERO
    equity_from_cash = sum((by_source.get(m, ZERO) for m in _EQUITY_SOURCES), ZERO)
    non_equity_cash = {m: v for m, v in by_source.items()
                       if m not in _EQUITY_SOURCES}

    # Equity does not only move through cash. An expense a customer settles
    # on the book's behalf (EquityExpense.paid_by_current_account) moves no money at
    # all — it posts a CurrentAccountMovement instead, reducing what they owe. Both
    # legs are real and both are already recorded; taking equity from the
    # cash journal alone counted the asset leg and dropped the equity one,
    # which inflated the residual by exactly those expenses.
    equity_ct = [ContentType.objects.get(app_label="accounting", model=m).pk
                 for m in _EQUITY_SOURCES
                 if ContentType.objects.filter(app_label="accounting", model=m).exists()]
    equity_from_current_account = CurrentAccountMovement.objects.filter(
        book=book, source_type_id__in=equity_ct
    ).aggregate(t=Sum("amount_base"))["t"] or ZERO
    equity = equity_from_cash + equity_from_current_account

    assets = cash + receivable + inventory + fixed
    residual = assets - payable - equity

    # Why it does not balance, in terms that add up to the residual.
    movement_types = [
        {"type": r["movement_type"], "n": r["n"], "amount": r["s"] or ZERO}
        for r in (CurrentAccountMovement.objects.filter(book=book)
                  .values("movement_type")
                  .annotate(n=Count("id"), s=Sum("amount_base"))
                  .order_by("-n"))
    ]
    current_account_net = sum((r["amount"] for r in movement_types), ZERO)

    causes = [
        {"label": "Current account ledger — movements with no contra anywhere",
         # The current account-funded equity rows DO have both legs, so they are not
         # part of the problem and must not be counted as if they were.
         "amount": current_account_net - equity_from_current_account},
        *[{"label": f"Cash moved by {m} (not income or capital)", "amount": v}
          for m, v in sorted(non_equity_cash.items())],
        {"label": "Inventory held, never posted", "amount": inventory},
        {"label": "Fixed assets held, never posted", "amount": fixed},
    ]

    return {
        "book": book,
        "cash": cash,
        "receivable": receivable,
        "payable": payable,
        "inventory": inventory,
        "unvalued_rolls": unvalued_rolls,
        "unvalued_metres": unvalued_metres,
        "fixed": fixed,
        "assets": assets,
        "liabilities": payable,
        "equity": equity,
        "equity_from_cash": equity_from_cash,
        "equity_from_current_account": equity_from_current_account,
        "equity_by_source": {m: by_source.get(m, ZERO) for m in _EQUITY_SOURCES},
        "liabilities_plus_equity": payable + equity,
        "residual": residual,
        "balanced": residual == ZERO,
        "causes": causes,
        # The identity: the causes account for the residual exactly. Shown
        # rather than asserted, so a future change that breaks it is visible
        # on the page instead of raising in the middle of a report.
        "causes_total": sum((c["amount"] for c in causes), ZERO),
        "movement_types": movement_types,
    }


def _inventory_value(book):
    """(value, unvalued roll count, unvalued metres) for a book's stock.

    Stock belongs to whoever owns the shelves it sits on. Warehouse
    .accounting_book is required on every warehouse that holds stock (only
    a combined view, which holds none, goes without), so the rolls in Ergene Fabrika are
    Ergene's whether or not anyone ever invoiced them.

    This used to scope by the purchase-invoice line the roll arrived on,
    which reported every book's inventory as zero: not one roll in the
    company carries a purchase_invoice_item, so the filter matched
    nothing and 100,888 metres of real fabric read as $0.00.

    Cost is what the item itself was stamped with at intake, falling
    back to the purchase-invoice line and then to the product's current
    cost for items received before the stamp existed. The item's own
    figure comes first because it is the only one that cannot move:
    cost_usd is a last-purchase price and the intake path rewrites it on
    every new batch, so valuing old stock by it revalues goods nobody
    re-bought.

    Only live items count — a consumed one is not an asset — and items
    with no cost basis at all are counted, not guessed at.
    """
    from django.db.models import DecimalField, ExpressionWrapper, F
    from django.db.models.functions import Coalesce

    try:
        from operating.models import WarehouseProductItem
    except ImportError:          # operating not installed — inventory is 0
        return ZERO, 0, ZERO

    money = DecimalField(max_digits=18, decimal_places=6)
    live = (WarehouseProductItem.objects
            .filter(product__warehouse__accounting_book=book,
                    status__in=("in_stock", "partial"))
            .exclude(quantity_remaining=None))

    unit_cost = Coalesce(F("unit_cost_base"),
                         F("purchase_invoice_item__unit_price"),
                         F("product__cost_usd"),
                         output_field=money)
    value = ExpressionWrapper(F("quantity_remaining") * unit_cost,
                              output_field=money)
    total = live.aggregate(v=Sum(value))["v"] or ZERO

    unvalued = live.filter(unit_cost_base=None, purchase_invoice_item=None,
                           product__cost_usd=None)
    return (
        Decimal(total).quantize(Decimal("0.01")),
        unvalued.count(),
        unvalued.aggregate(m=Sum("quantity_remaining"))["m"] or ZERO,
    )


# ---------------------------------------------------------------------------
# Reconciliation
#
# A control account is a summary of a subsidiary ledger, and the only thing
# that makes it a control account rather than a number is that the two can be
# checked against each other. Nothing checked them, which is how the books
# got to $1.67M out without any single page being wrong.
#
# Each row below is one such check, and each is honest about the difference
# rather than about whether the difference is acceptable. A row that does not
# reconcile names what is missing, because "off by 4,312.90" is a fact and
# "the ledger is broken" is not.
# ---------------------------------------------------------------------------
def _cash_journal_total(book):
    from .models import CashTransactionEntry
    return (CashTransactionEntry.objects.filter(book=book)
            .aggregate(t=Sum(_signed_cash()))["t"] or ZERO)


def _current_account_net(book):
    from .models_accounts import CurrentAccount
    return (CurrentAccount.objects.filter(book=book)
            .aggregate(t=Sum("cached_balance"))["t"] or ZERO)


def reconcile(book, date_to=None):
    """Every control account against the ledger it summarises.

    Returns a list of rows and whether they all agree. `ledger` is what the
    general ledger says; `subsidiary` is what the detail says; `note`
    explains a difference where the cause is already known, so that a gap
    nobody has explained yet stands out from one that is simply the next
    job.

    Receivables and payables are checked as a NET, because that is what the
    subsidiary ledger holds. Every movement posts to 1200 regardless of
    which way the account ends up, and reclassify_payables moves the credit
    balances across afterwards; 1200 less 2000 is therefore the figure to
    compare, both before that entry is made and after.
    """
    # One pass over the ledger rather than a query per account: the trial
    # balance already groups every line by account, and the codes below are
    # just a lookup into it. An account with no lines is absent from it and
    # is worth zero, which is why this reads through .get().
    tb = trial_balance(book=book, date_to=date_to)
    by_code = {r["code"]: r["balance"] for r in tb["rows"]}

    def balance(code):
        return by_code.get(code, ZERO)

    inventory, _unvalued, _metres = _inventory_value(book)

    rows = [
        {
            "label": "Receivables less payables",
            "control": "1200 − 2000",
            "ledger": balance("1200") - balance("2000"),
            "subsidiary": _current_account_net(book),
            "subsidiary_label": "Sum of current account balances",
            "note": "",
        },
        {
            "label": "Cash and bank",
            "control": "1000",
            "ledger": balance("1000"),
            "subsidiary": _cash_journal_total(book),
            "subsidiary_label": "Cash journal",
            "note": "Transfers and currency exchanges move cash on both "
                    "legs and are not posted yet, so they sit in this gap.",
        },
        {
            "label": "Inventory",
            "control": "1300",
            "ledger": balance("1300"),
            "subsidiary": inventory,
            "subsidiary_label": "Stock on the shelves, at cost",
            # Goods leaving now relieve stock as they go (services_posting
            # .post_stock_movement), so what is left of this gap is stock
            # that ARRIVED without a purchase invoice behind it, plus the
            # history that predates the posting.
            "note": "Stock that arrives without a purchase invoice raises "
                    "the shelves and not the ledger. Goods leaving on a "
                    "sale do relieve stock, but only since that posting "
                    "began: anything older is still in this difference.",
        },
    ]
    for row in rows:
        row["difference"] = row["ledger"] - row["subsidiary"]
        row["reconciled"] = row["difference"] == ZERO

    # Not reconciliations: two holding accounts whose balance IS the
    # outstanding work. Zero when there is none left.
    pending = [
        {"label": "Suspense", "code": "1900", "balance": balance("1900"),
         "note": "Movements whose other leg nobody has decided."},
        {"label": "Inter-company clearing", "code": "1950",
         "balance": balance("1950"),
         "note": "Mirrored movements whose reason lives in the other book."},
    ]

    return {
        "book": book,
        "date_to": date_to,
        "rows": rows,
        "pending": [p for p in pending if p["balance"] != ZERO],
        "trial_balance_balanced": tb["balanced"],
        "trial_balance_difference": tb["difference"],
        "all_reconciled": all(r["reconciled"] for r in rows),
    }


def unbalanced_entries(book=None):
    """Entries whose lines do not agree, which should be none of them.

    post_entry cannot write one, so anything here arrived another way — a
    hand-edited row, a restored dump, a migration that wrote lines
    directly. Worth asking precisely because the answer should be boring.
    """
    from .models_ledger import JournalEntry

    entries = JournalEntry.objects.all()
    if book is not None:
        entries = entries.filter(book=book)
    bad = []
    for entry in entries.annotate(d=Sum("lines__debit"), c=Sum("lines__credit")):
        debit, credit = entry.d or ZERO, entry.c or ZERO
        if debit != credit:
            bad.append({"entry": entry, "debit": debit, "credit": credit,
                        "difference": debit - credit})
    return bad


def suspense_report(book, limit=10):
    """What is sitting in 1900 Suspense on this book, and what put it there.

    Suspense is a promise that somebody will come back and say what an
    amount really was. A balance nobody looks at is a promise nobody keeps,
    so the book page shows this whenever the balance is not zero.

    Items are the movements behind the parked lines, newest first, each
    with the screen that can reclassify it: the payment form for a payment
    made by offset or "other", the movement form for everything else.
    Transfer legs are counted but not listed — a transfer's two halves park
    equal and opposite amounts, so they are not a decision anyone owes.
    """
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse

    from .models_accounts import (CurrentAccountMovement,
                                  CurrentAccountTransfer, Payment)

    lines = JournalLine.objects.filter(entry__book=book, account__code="1900")
    totals = lines.aggregate(d=Sum("debit"), c=Sum("credit"))
    balance = (totals["d"] or ZERO) - (totals["c"] or ZERO)

    movement_ct = ContentType.objects.get_for_model(CurrentAccountMovement)
    transfer_ct = ContentType.objects.get_for_model(CurrentAccountTransfer)
    payment_ct = ContentType.objects.get_for_model(Payment)

    movement_ids = (lines.filter(entry__source_type=movement_ct)
                    .values_list("entry__source_id", flat=True))
    movements = (CurrentAccountMovement.objects
                 .filter(pk__in=movement_ids)
                 .exclude(source_type=transfer_ct)
                 .select_related("current_account")
                 .order_by("-date", "-id"))

    items = []
    for mv in movements[:limit]:
        if mv.source_type_id == payment_ct.pk and mv.source_id:
            url = reverse("accounts:payment_edit", kwargs={"pk": mv.source_id})
        else:
            payment = Payment.objects.filter(posted_movement=mv).only("pk").first()
            url = (reverse("accounts:payment_edit", kwargs={"pk": payment.pk})
                   if payment else
                   reverse("accounts:movement_edit",
                           kwargs={"pk": mv.current_account_id, "mv_pk": mv.pk}))
        items.append({"movement": mv, "account": mv.current_account,
                      "amount": mv.amount_base, "url": url})

    return {
        "balance": balance,
        "items": items,
        "count": movements.count(),
    }
