"""
Current-account reports (Phase 4).

    /accounting/accounts/reports/                → ReportIndex (landing page)
    /accounting/accounts/reports/trial-balance/  → TrialBalance    (current account mizan per book, period filter)
    /accounting/accounts/reports/credit-limit/   → CreditLimitReport
    /accounting/books/<id>/reports/chart-of-accounts/ → ChartOfAccounts
"""
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from accounting.models import Book
from .models import CurrentAccount, CurrentAccountMovement
from .models_ledger import ChartAccount


# ---------------------------------------------------------------------------
# Landing
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class ReportIndex(View):
    template_name = "accounts/report_index.html"

    def get(self, request):
        over_limit_count = (
            CurrentAccount.objects
            .filter(is_active=True, credit_limit__gt=0)
            .extra(where=["cached_balance > credit_limit"])
            .count()
        )

        return render(request, self.template_name, {
            "over_limit_count":   over_limit_count,
        })


# ---------------------------------------------------------------------------
# 2. Trial Balance — Current account Mizan
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class TrialBalance(View):
    template_name = "accounts/report_trial_balance.html"

    def get(self, request):
        today = timezone.now().date()
        date_from = request.GET.get("date_from") or ""
        date_to   = request.GET.get("date_to")   or today.isoformat()
        book_id   = str(request.book.pk)
        zero_filter = request.GET.get("zero") or "hide"   # show | hide

        if not date_from:
            # Default: start of current year
            date_from = today.replace(month=1, day=1).isoformat()

        # Get all current accounts (filtered by book if specified)
        current_account_qs = CurrentAccount.objects.select_related("book", "default_currency").filter(is_active=True)
        if book_id.isdigit():
            current_account_qs = current_account_qs.filter(book_id=int(book_id))

        # Per-current account aggregations
        # opening = sum movements before date_from
        # debits  = sum positive movements in [date_from, date_to]
        # credits = sum negative movements in [date_from, date_to]
        # closing = opening + debits + credits
        # One grouped aggregate for every account, not three per account in
        # a Python loop. Laleli has 1,277 active accounts, so the loop was
        # 3,831 round trips to a database at the end of a proxy connection
        # and the page took minutes to answer. The same three figures fall
        # out of a single query with filtered aggregates.
        #
        # amount_base, not amount. `amount` is what was ENTERED, in
        # whatever currency the movement was written in, and this page adds
        # those together: 877 dollar movements, 16 lira and 2 euro on
        # Laleli, six accounts holding more than one currency, all summed
        # as though a lira were a dollar. The grand total read 302,676.10
        # against a real position of 349,327.22 — understated by 46,651.12
        # by an addition that was never meaningful. amount_base is what
        # cached_balance and the balance sheet already use, so the mizan
        # now agrees with the account pages instead of quietly contradicting
        # them. Every figure on the page is the book's base currency, which
        # the header now says out loud.
        ZERO = Decimal("0.00")
        totals = {
            r["current_account_id"]: r
            for r in (CurrentAccountMovement.objects
                      .filter(current_account__in=current_account_qs, date__lte=date_to)
                      .values("current_account_id")
                      .annotate(
                          opening=Sum("amount_base", filter=Q(date__lt=date_from)),
                          debits=Sum("amount_base", filter=Q(date__gte=date_from,
                                                             amount_base__gt=0)),
                          credits=Sum("amount_base", filter=Q(date__gte=date_from,
                                                              amount_base__lt=0)),
                      ))
        }

        rows = []
        for current_account in current_account_qs:
            # An account with no movements at all is absent from the
            # aggregate rather than present with zeros.
            t = totals.get(current_account.pk)
            opening = (t["opening"] if t and t["opening"] is not None else ZERO)
            debits = (t["debits"] if t and t["debits"] is not None else ZERO)
            credits = (t["credits"] if t and t["credits"] is not None else ZERO)
            closing = opening + debits + credits

            if zero_filter == "hide" and opening == 0 and debits == 0 and credits == 0:
                continue

            rows.append({
                "current_account":    current_account,
                "opening": opening,
                "debits":  debits,
                "credits": abs(credits),
                "closing": closing,
            })

        rows.sort(key=lambda r: r["current_account"].code)

        # Grand totals
        g_opening = sum((r["opening"] for r in rows), Decimal("0.00"))
        g_debits  = sum((r["debits"]  for r in rows), Decimal("0.00"))
        g_credits = sum((r["credits"] for r in rows), Decimal("0.00"))
        g_closing = sum((r["closing"] for r in rows), Decimal("0.00"))

        return render(request, self.template_name, {
            "rows": rows,
            "g_opening": g_opening,
            "g_debits": g_debits,
            "g_credits": g_credits,
            "g_closing": g_closing,
            "date_from": date_from,
            "date_to": date_to,
            "filter_book": book_id,
            "base_currency": getattr(request.book, "base_currency", None),
            "zero_filter": zero_filter,
            "books": Book.objects.all().order_by("name"),
        })


# ---------------------------------------------------------------------------
# 3. Credit Limit Report — Risk Limiti
# ---------------------------------------------------------------------------
@method_decorator(login_required, name="dispatch")
class CreditLimitReport(View):
    template_name = "accounts/report_credit_limit.html"

    def get(self, request):
        book_id = str(request.book.pk)
        view = request.GET.get("view") or "over"  # over | near | all

        qs = (CurrentAccount.objects
              .select_related("book", "default_currency")
              .filter(is_active=True, credit_limit__gt=0))

        if book_id.isdigit():
            qs = qs.filter(book_id=int(book_id))

        rows = []
        for c in qs:
            if c.credit_limit <= 0:
                continue
            usage_pct = (c.cached_balance / c.credit_limit * 100) if c.credit_limit else Decimal("0")
            available = c.credit_limit - c.cached_balance

            row = {
                "current_account": c,
                "balance": c.cached_balance,
                "credit_limit": c.credit_limit,
                "usage_pct": usage_pct,
                "available": available,
                "is_over": c.cached_balance > c.credit_limit,
                "is_near": usage_pct >= 80 and c.cached_balance <= c.credit_limit,
            }

            if view == "over" and not row["is_over"]:
                continue
            if view == "near" and not (row["is_near"] or row["is_over"]):
                continue
            rows.append(row)

        rows.sort(key=lambda r: -r["usage_pct"])

        return render(request, self.template_name, {
            "rows": rows,
            "view": view,
            "filter_book": book_id,
            "books": Book.objects.all().order_by("name"),
        })


@method_decorator(login_required, name="dispatch")
class ChartOfAccounts(View):
    """Every ledger code, what it means, what posts to it and its balance.

    The codes turn up on the movement form's preview and on the balance
    sheet with nothing to say what 4000 or 1900 is; this is where they are
    looked up.
    """
    template_name = "accounts/report_chart_of_accounts.html"

    def get(self, request):
        from .services_posting import chart_of_accounts

        rows = chart_of_accounts(request.book)
        groups = []
        for kind, label in ChartAccount.TYPES:
            members = [r for r in rows if r["type"] == kind]
            if members:
                groups.append({"type": kind, "label": label, "rows": members})
        return render(request, self.template_name, {"groups": groups})


def _subsidiary_ledgers(book, rec):
    """Each subsidiary ledger beside the ledger account it is the detail of.

    The general ledger holds one total per account; a subsidiary ledger
    says what that total is made of — which cash account, which customer,
    which warehouse. They are shown one by one, each against its own
    control account, and never added into an equation of their own: they
    hold no equity, so that sum cannot balance.

    `rec` is reconcile()'s answer, which already has both totals for each.
    """
    from django.urls import reverse
    from django.utils.translation import gettext as _

    from .services_ledger import _inventory_value, cash_by_account

    ZERO = Decimal("0.00")
    names = dict(ChartAccount.objects
                 .filter(code__in=("1000", "1200", "1300", "2000"))
                 .values_list("code", "name"))
    by_control = {r["control"]: r for r in rec["rows"]}

    def card(control, **kwargs):
        row = by_control[control]
        # Positive when the records hold more than the ledger has been told.
        gap = row["subsidiary"] - row["ledger"]
        return {
            "records": row["subsidiary"],
            "ledger": row["ledger"],
            "agrees": gap == ZERO,
            "records_show_more": gap > ZERO,
            "gap": abs(gap),
            "why": _(row["note"]) if row["note"] else _(
                "Movements recorded before automatic posting began have "
                "not been replayed into the general ledger yet."),
            **kwargs,
        }

    # ── Cash journal: one line per cash account ──────────────────────
    base_code = book.base_currency.code if book.base_currency_id else ""
    cash_lines = [
        {"label": (f'{r["name"]} ({r["currency"]})' if r["name"]
                   else _("No cash account")),
         "amount": r["base"],
         # What a hand count would find, for a till not kept in the
         # book's own currency — there the two figures are the same.
         "native": r["native"] if r["currency"] != base_code else None,
         "currency": r["currency"]}
        for r in cash_by_account(book)
    ]

    # ── Current accounts: who owes us, and whom we owe ───────────────
    accounts = CurrentAccount.objects.filter(book=book)
    owed_to_us = accounts.filter(cached_balance__gt=0)
    owed_by_us = accounts.filter(cached_balance__lt=0)
    account_lines = [
        {"label": _("Accounts that owe us"), "count": owed_to_us.count(),
         "amount": owed_to_us.aggregate(t=Sum("cached_balance"))["t"] or ZERO},
        {"label": _("Accounts we owe"), "count": owed_by_us.count(),
         "amount": owed_by_us.aggregate(t=Sum("cached_balance"))["t"] or ZERO},
    ]

    # ── Warehouse stock: one line per warehouse this book owns ───────
    stock_lines, unvalued = [], 0
    try:
        from operating.models import Warehouse
        warehouses = Warehouse.objects.filter(accounting_book=book).order_by("name")
    except ImportError:
        warehouses = []
    for warehouse in warehouses:
        value, missing, _qty = _inventory_value(book, warehouse=warehouse)
        unvalued += missing
        if value or missing:
            stock_lines.append({
                "label": warehouse.name, "amount": value,
                "url": reverse("operating:warehouse_detail", args=[warehouse.pk]),
            })

    return [
        card("1000",
             title=_("Cash journal"), icon="wallet",
             what=_("Every cash and bank transaction, by cash account."),
             controls=[("1000", names.get("1000", ""))],
             lines=cash_lines,
             url=reverse("accounting:cash_transaction_entry_list", args=[book.pk]),
             url_label=_("Open the cash journal")),
        card("1200 − 2000",
             title=_("Current accounts"), icon="users",
             what=_("Every customer and supplier account, with its movements."),
             controls=[("1200", names.get("1200", "")),
                       ("2000", names.get("2000", ""))],
             controls_joiner=_("less"),
             lines=account_lines,
             url=reverse("accounts:list", args=[book.pk]),
             url_label=_("Open the current accounts")),
        card("1300",
             title=_("Warehouse stock"), icon="package",
             what=_("Every stock item on the shelves, at its cost."),
             controls=[("1300", names.get("1300", ""))],
             lines=stock_lines,
             unvalued=unvalued,
             url=reverse("operating:warehouse_list"),
             url_label=_("Open the warehouses")),
    ]


@method_decorator(login_required, name="dispatch")
class BalanceSheet(View):
    """Assets = Liabilities + Equity, from the general ledger.

    The equation is true there by construction, because an unbalanced
    entry cannot be written. Under it, each subsidiary ledger is set
    against the control account it is the detail of — the cash journal,
    the current accounts, the warehouse stock — which is where a ledger
    that has fallen behind shows. See _subsidiary_ledgers.

    The records were once totalled into an equation of their own beside
    this one. They hold no equity, so that column could never balance and
    only ever reported a book's whole equity as an error.
    """
    template_name = "accounts/report_balance_sheet.html"

    def get(self, request):
        from .services_ledger import (balance_sheet, reconcile,
                                       subsidiary_equation)

        date_to = request.GET.get("date_to") or None
        gl = balance_sheet(request.book, date_to=date_to)
        subs = subsidiary_equation(request.book)
        # What each control account says against the ledger it summarises.
        rec = reconcile(request.book, date_to=date_to)

        # How far the ledger has come. Zero when nothing is posted yet; 100
        # when the two agree on total assets.
        coverage = None
        if subs["assets"]:
            coverage = (gl["assets"] / subs["assets"] * 100).quantize(
                Decimal("0.1"))

        return render(request, self.template_name, {
            "gl": gl,
            "rec": rec,
            "ledgers": _subsidiary_ledgers(request.book, rec),
            "coverage": coverage,
            "date_to": date_to or "",
        })


@method_decorator(login_required, name="dispatch")
class LedgerAccount(View):
    """One ledger account: every entry behind its balance.

    The balance sheet, the chart of accounts and the book page each print a
    figure per account and nothing said what it was made of. Some of what
    makes it up exists nowhere else — an opening correction, a
    reclassification out of Suspense, the entries that keep Accounts
    Payable in step with the accounts in credit (reference AP-RESPLIT) —
    because those are entries with no movement on anybody's statement.

    Newest last, with a running balance, so the last row is the figure the
    other pages print. An account with a long history shows its latest
    LIMIT rows and carries everything before them as one opening line,
    which keeps the running balance true without loading ten thousand rows.
    """
    template_name = "accounts/report_ledger_account.html"
    LIMIT = 500

    def get(self, request, code):
        from django.db.models import Sum
        from django.http import Http404
        from django.urls import reverse
        from .models_ledger import JournalLine

        account = ChartAccount.objects.filter(code=code).first()
        if account is None:
            raise Http404("No such ledger account.")
        debit_normal = account.type in (ChartAccount.ASSET, ChartAccount.EXPENSE)

        def signed(debit, credit):
            debit, credit = debit or Decimal("0"), credit or Decimal("0")
            return (debit - credit) if debit_normal else (credit - debit)

        def total(qs):
            agg = qs.aggregate(d=Sum("debit"), c=Sum("credit"))
            return signed(agg["d"], agg["c"])

        date_from = request.GET.get("date_from") or ""
        date_to = request.GET.get("date_to") or ""
        base = JournalLine.objects.filter(entry__book=request.book, account=account)
        opening = Decimal("0")
        in_range = base
        if date_from:
            opening = total(base.filter(entry__date__lt=date_from))
            in_range = in_range.filter(entry__date__gte=date_from)
        if date_to:
            in_range = in_range.filter(entry__date__lte=date_to)

        count = in_range.count()
        ordered = (in_range.select_related("entry", "current_account", "cash_account")
                   .order_by("entry__date", "entry_id", "pk"))
        hidden = max(0, count - self.LIMIT)
        lines = list(ordered[hidden:])
        if hidden:
            # Everything in range before the rows shown, folded into the
            # opening line: the range total less what is on the page.
            shown = sum((signed(l.debit, l.credit) for l in lines), Decimal("0"))
            opening += total(in_range) - shown

        # The other side of each entry, so a row says what it was against
        # without opening the entry: "Accounts Receivable (1200)".
        others = {}
        for other in (JournalLine.objects
                      .filter(entry_id__in={l.entry_id for l in lines})
                      .exclude(account=account).select_related("account")):
            label = f"{other.account.name} ({other.account.code})"
            bucket = others.setdefault(other.entry_id, [])
            if label not in bucket:
                bucket.append(label)

        running = opening
        rows = []
        for line in lines:
            running += signed(line.debit, line.credit)
            party = line.current_account
            rows.append({
                "line": line,
                "entry": line.entry,
                "text": line.memo or line.entry.description,
                "against": others.get(line.entry_id, []),
                "party": party,
                "party_url": (reverse("accounts:statement", args=[party.pk])
                              if party is not None else ""),
                "balance": running,
            })

        return render(request, self.template_name, {
            "account": account,
            "account_label": f"{account.name} ({account.code})",
            "rows": rows,
            "opening": opening,
            "closing": running,
            "show_opening": bool(date_from or hidden),
            "hidden": hidden,
            "count": count,
            "date_from": date_from,
            "date_to": date_to,
            "debit_total": sum((l.debit for l in lines), Decimal("0")),
            "credit_total": sum((l.credit for l in lines), Decimal("0")),
        })
