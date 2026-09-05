"""The general ledger — the one place where the accounting equation is true.

Everything else in this app is a SUBSIDIARY ledger: the cari accounts know
what each customer owes, the cash journal knows what each account holds,
the warehouse knows what stock sits on the shelves. Each is correct about
its own subject and none of them says anything about the others, so
Assets = Liabilities + Equity has never been enforced anywhere — it has
only ever been something you could compute afterwards and find untrue.

On the two live books it is untrue by $351,564.45 and $1,319,947.21,
because almost nothing posts a contra entry: 712 opening movements created
receivables with nothing on the other side, 62 of 82 payments reduced a
receivable without cash landing anywhere, and 34 sales moved a balance
without recording revenue.

A journal entry fixes that by construction. An entry is a set of lines
whose debits equal their credits, and it is refused if they do not — so
the equation cannot drift, because there is no way to write a row that
would break it. The balance sheet then stops being a calculation someone
has to defend and becomes a query.

Three models:

  ChartAccount  the named lines a balance sheet and P&L are made of.
                Shared across books — each book is a separate business
                but they are the same KIND of business, and one chart
                means the two can be compared line for line.

  JournalEntry  one business event, on one book, on one date. Carries a
                generic link back to whatever caused it, so a ledger row
                can always be traced to the document it came from.

  JournalLine   one account, one amount, one side. The subsidiary links
                (cari, cash_account) are what let a control account be
                reconciled against the ledger it summarises.

Nothing posts to these yet. Wiring the existing paths and backfilling
history are separate jobs — see services_ledger.post_entry.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from authentication.models import Member

from .models import Book, CashAccount, CurrencyCategory

ZERO = Decimal("0.00")


class ChartAccount(models.Model):
    """A named line on the balance sheet or the P&L.

    Codes follow the usual blocks — 1 asset, 2 liability, 3 equity,
    4 revenue, 5 expense — so sorting by code sorts into statement order
    without a second field to keep in step with the type.
    """

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"

    TYPES = [
        (ASSET, _("Asset")),
        (LIABILITY, _("Liability")),
        (EQUITY, _("Equity")),
        (REVENUE, _("Revenue")),
        (EXPENSE, _("Expense")),
    ]

    # Which side of an entry INCREASES this kind of account. Assets and
    # expenses are debit-normal; everything else is credit-normal. This is
    # the whole of the sign convention, written once.
    DEBIT_NORMAL = {ASSET, EXPENSE}

    # Where each type belongs in the equation. Revenue and expense are
    # equity in the end — they are the year's movement in it — but they
    # are reported separately until the books are closed.
    BALANCE_SHEET = {ASSET, LIABILITY, EQUITY}

    code = models.CharField(max_length=10, unique=True, help_text="e.g. 1200")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=12, choices=TYPES)
    description = models.TextField(blank=True)

    # A control account is summarised by a subsidiary ledger elsewhere —
    # 1200 Accounts Receivable by the cari accounts, 1000 Cash by the cash
    # journal. Flagged so a reconciliation report can find them without a
    # hardcoded list of codes.
    is_control = models.BooleanField(
        default=False,
        help_text="Summarises a subsidiary ledger (cari accounts, cash accounts).",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = _("Chart Account")
        verbose_name_plural = _("Chart of Accounts")

    def __str__(self):
        return f"{self.code} {self.name}"

    @property
    def is_debit_normal(self):
        return self.type in self.DEBIT_NORMAL

    def balance(self, book=None, date_to=None):
        """This account's balance, in the direction it normally runs.

        A debit-normal account returns debits minus credits; a
        credit-normal one the other way round. So every account reports a
        positive number when it holds what it is supposed to hold, and the
        caller does not have to remember which way round this one goes.
        """
        lines = self.lines.all()
        if book is not None:
            lines = lines.filter(entry__book=book)
        if date_to is not None:
            lines = lines.filter(entry__date__lte=date_to)
        totals = lines.aggregate(d=Sum("debit"), c=Sum("credit"))
        debit = totals["d"] or ZERO
        credit = totals["c"] or ZERO
        return debit - credit if self.is_debit_normal else credit - debit


class JournalEntry(models.Model):
    """One business event, balanced.

    The entry owns the date, the book and the story; the lines own the
    money. An entry with unbalanced lines is not an entry — see
    services_ledger.post_entry, which is the only supported way to make
    one, and `assert_balanced` below, which is what the audit command and
    the tests check.
    """

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="journal_entries")

    # When the event happened, not when it was typed. Same distinction the
    # cash journal already draws, and for the same reason: a backdated
    # payment belongs in the period it was made, not the one it was
    # entered in.
    date = models.DateField()
    description = models.CharField(max_length=300)

    # Batch marker, so a backfill or an import can be found and undone as
    # a unit. Mirrors CariMovement.reference and the ERGENE-OB-* pattern.
    reference = models.CharField(max_length=60, blank=True, db_index=True)

    # What caused this entry — a Payment, an Invoice, a CariMovement, an
    # EquityExpense. Generic because the list will keep growing, and a
    # ledger row that cannot name its cause is a ledger row nobody can
    # check.
    source_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    source_id = models.PositiveIntegerField(null=True, blank=True)
    source = GenericForeignKey("source_type", "source_id")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        Member, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="journal_entries",
    )

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = _("Journal Entry")
        verbose_name_plural = _("Journal Entries")
        indexes = [
            models.Index(fields=["book", "date"]),
            models.Index(fields=["source_type", "source_id"]),
        ]

    def __str__(self):
        return f"#{self.pk} {self.date} {self.description[:40]}"

    def totals(self):
        agg = self.lines.aggregate(d=Sum("debit"), c=Sum("credit"))
        return (agg["d"] or ZERO), (agg["c"] or ZERO)

    @property
    def total_debit(self):
        return self.totals()[0]

    @property
    def total_credit(self):
        return self.totals()[1]

    @property
    def is_balanced(self):
        debit, credit = self.totals()
        return debit == credit

    def assert_balanced(self):
        """Raise unless the lines balance.

        Called by post_entry after the lines are written, inside the same
        transaction, so an unbalanced entry is rolled back rather than
        stored and reported later. An entry with no lines at all is
        refused too — it balances trivially and means nothing.
        """
        debit, credit = self.totals()
        if not self.lines.exists():
            raise ValidationError(f"Journal entry {self.pk} has no lines.")
        if debit != credit:
            raise ValidationError(
                f"Journal entry {self.pk} does not balance: "
                f"debits {debit} vs credits {credit} "
                f"(out by {debit - credit})."
            )


class JournalLine(models.Model):
    """One account, one amount, one side.

    Amounts are BASE currency, always — the ledger has one unit or its
    totals mean nothing, which is the mistake the trial-balance report
    still makes by summing entered amounts across USD, TRY and EUR. What
    was actually entered is kept alongside in `amount_original` and
    `currency` so an FX difference can be explained rather than merely
    absorbed.
    """

    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(ChartAccount, on_delete=models.PROTECT, related_name="lines")

    # Exactly one of these is non-zero. Two columns rather than one signed
    # amount because that is how a ledger is read, and because "which side"
    # then cannot be lost to a sign flip somewhere upstream.
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)

    # What was entered, before conversion. Null when the entry was already
    # in base currency.
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.PROTECT, null=True, blank=True
    )
    amount_original = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    exchange_rate = models.DecimalField(
        max_digits=18, decimal_places=8, null=True, blank=True
    )

    # Subsidiary links. A control account's balance has to be reconcilable
    # against the ledger that summarises it, and that is only possible if
    # each line says which customer or which cash account it was for.
    cari = models.ForeignKey(
        "accounting.CariAccount", on_delete=models.PROTECT,
        null=True, blank=True, related_name="journal_lines",
    )
    cash_account = models.ForeignKey(
        CashAccount, on_delete=models.PROTECT,
        null=True, blank=True, related_name="journal_lines",
    )

    memo = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["entry", "id"]
        verbose_name = _("Journal Line")
        verbose_name_plural = _("Journal Lines")
        constraints = [
            # A line is one side or the other, never both and never
            # neither. Enforced in the database because this is the
            # invariant every balance downstream rests on.
            models.CheckConstraint(
                check=(
                    models.Q(debit__gt=0, credit=0)
                    | models.Q(credit__gt=0, debit=0)
                ),
                name="journal_line_one_side_only",
            ),
            models.CheckConstraint(
                check=models.Q(debit__gte=0) & models.Q(credit__gte=0),
                name="journal_line_no_negative_amounts",
            ),
        ]
        indexes = [
            models.Index(fields=["account"]),
            models.Index(fields=["cari"]),
        ]

    def __str__(self):
        side = f"Dr {self.debit}" if self.debit else f"Cr {self.credit}"
        return f"{self.account.code} {side}"

    @property
    def signed(self):
        """The line as a single number, positive on the debit side."""
        return self.debit - self.credit
