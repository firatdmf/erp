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


def account(code):
    """The chart account with this code, or a clear error.

    Raising beats returning None: a posting rule that silently skipped a
    leg would write a half-entry, and post_entry would then reject the
    whole event for a reason that points at the wrong place.
    """
    try:
        return ChartAccount.objects.get(code=code)
    except ChartAccount.DoesNotExist:
        raise ValidationError(
            f"No chart account {code!r}. Run accounting.services_ledger."
            f"ensure_chart() or the seed_chart_of_accounts command."
        )


def debit(code, amount, **kwargs):
    """A debit line, for handing to post_entry."""
    return _line(code, debit=amount, **kwargs)


def credit(code, amount, **kwargs):
    """A credit line, for handing to post_entry."""
    return _line(code, credit=amount, **kwargs)


def _line(code, debit=ZERO, credit=ZERO, *, cari=None, cash_account=None,
          currency=None, amount_original=None, exchange_rate=None, memo=""):
    return {
        "code": code,
        "debit": Decimal(debit or 0).quantize(Decimal("0.01")),
        "credit": Decimal(credit or 0).quantize(Decimal("0.01")),
        "cari": cari,
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
            cari=spec["cari"],
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
    (The report currently called "Trial Balance" in this app is a per-cari
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
#     residual = net cari position
#              + cash that moved for a non-equity reason
#              + inventory held
#              + fixed assets held
#
# which is an identity, not an estimate: every cari movement lacks an equity
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

    Every figure is base currency. Inventory is valued only where a cost
    basis exists — rolls received before purchase invoicing have none, and
    the count of those is returned beside the value so an unvalued asset
    cannot quietly read as a zero one.
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Count, F, DecimalField, ExpressionWrapper, Q

    from .models import AssetFixedAsset, CashTransactionEntry
    from .models_accounts import CariAccount, CariMovement

    entries = CashTransactionEntry.objects.filter(book=book)
    signed = _signed_cash()

    cash = entries.aggregate(t=Sum(signed))["t"] or ZERO

    cari = CariAccount.objects.filter(book=book)
    receivable = cari.filter(cached_balance__gt=0).aggregate(
        t=Sum("cached_balance"))["t"] or ZERO
    payable = -(cari.filter(cached_balance__lt=0).aggregate(
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
    # on the book's behalf (EquityExpense.paid_by_cari) moves no money at
    # all — it posts a CariMovement instead, reducing what they owe. Both
    # legs are real and both are already recorded; taking equity from the
    # cash journal alone counted the asset leg and dropped the equity one,
    # which inflated the residual by exactly those expenses.
    equity_ct = [ContentType.objects.get(app_label="accounting", model=m).pk
                 for m in _EQUITY_SOURCES
                 if ContentType.objects.filter(app_label="accounting", model=m).exists()]
    equity_from_cari = CariMovement.objects.filter(
        book=book, source_type_id__in=equity_ct
    ).aggregate(t=Sum("amount_base"))["t"] or ZERO
    equity = equity_from_cash + equity_from_cari

    assets = cash + receivable + inventory + fixed
    residual = assets - payable - equity

    # Why it does not balance, in terms that add up to the residual.
    movement_types = [
        {"type": r["movement_type"], "n": r["n"], "amount": r["s"] or ZERO}
        for r in (CariMovement.objects.filter(book=book)
                  .values("movement_type")
                  .annotate(n=Count("id"), s=Sum("amount_base"))
                  .order_by("-n"))
    ]
    cari_net = sum((r["amount"] for r in movement_types), ZERO)

    causes = [
        {"label": "Cari ledger — movements with no contra anywhere",
         # The cari-funded equity rows DO have both legs, so they are not
         # part of the problem and must not be counted as if they were.
         "amount": cari_net - equity_from_cari},
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
        "equity_from_cari": equity_from_cari,
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

    Cost comes from the purchase-invoice line a roll arrived on. Rolls
    received before purchase invoicing existed have no cost basis at all,
    and there is no honest way to invent one — so they are counted, not
    guessed at.
    """
    from django.db.models import Count, DecimalField, ExpressionWrapper, F

    try:
        from operating.models import WarehouseProductRoll
    except ImportError:          # operating not installed — inventory is 0
        return ZERO, 0, ZERO

    rolls = WarehouseProductRoll.objects.filter(
        purchase_invoice_item__invoice__book=book)
    value = ExpressionWrapper(
        F("meters_remaining") * F("purchase_invoice_item__unit_price"),
        output_field=DecimalField(max_digits=16, decimal_places=4))
    priced = rolls.exclude(meters_remaining=None)
    total = priced.aggregate(v=Sum(value))["v"] or ZERO

    # Unpriced rolls carry no invoice, so they cannot be filtered by book at
    # all — they are reported whole, which is itself part of the problem.
    unpriced = WarehouseProductRoll.objects.filter(purchase_invoice_item=None)
    return (
        Decimal(total).quantize(Decimal("0.01")),
        unpriced.count(),
        unpriced.aggregate(m=Sum("meters_remaining"))["m"] or ZERO,
    )
