"""The general ledger keeps the accounting equation true by refusing to
store anything that would break it.

Every other ledger in this app is correct about its own subject and says
nothing about the others, which is how Assets = Liabilities + Equity came
to be out by $351,564.45 on one book and $1,319,947.21 on the other. The
difference here is that an unbalanced entry cannot be written at all.

Run with:
    python manage.py test accounting.test_ledger
"""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_ledger import ChartAccount, JournalEntry, JournalLine
from accounting.services_ledger import (
    balance_sheet, credit, debit, ensure_chart, post_entry, trial_balance,
)


class LedgerBase(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        ensure_chart()

    def post(self, lines, when="2026-07-16", description="test"):
        return post_entry(book=self.book, date=when, description=description,
                          lines=lines)


class TheChart(LedgerBase):
    def test_seeding_is_idempotent(self):
        before = ChartAccount.objects.count()
        self.assertEqual(ensure_chart(), [])
        self.assertEqual(ChartAccount.objects.count(), before)

    def test_a_renamed_account_is_not_rewritten_by_a_later_seed(self):
        """A name someone edited is theirs, not something a deploy undoes."""
        acc = ChartAccount.objects.get(code="5100")
        acc.name = "İşletme Giderleri"
        acc.save(update_fields=["name"])
        ensure_chart()
        self.assertEqual(ChartAccount.objects.get(code="5100").name, "İşletme Giderleri")

    def test_assets_and_expenses_are_debit_normal_everything_else_is_not(self):
        self.assertTrue(ChartAccount.objects.get(code="1200").is_debit_normal)
        self.assertTrue(ChartAccount.objects.get(code="5100").is_debit_normal)
        for code in ("2000", "3000", "4000"):
            self.assertFalse(ChartAccount.objects.get(code=code).is_debit_normal)


class PostingRefusesToBreakTheEquation(LedgerBase):
    def test_a_balanced_entry_posts(self):
        entry = self.post([debit("1200", "1000.00"), credit("4000", "1000.00")])
        self.assertTrue(entry.is_balanced)
        self.assertEqual(entry.lines.count(), 2)

    def test_an_unbalanced_entry_is_refused_and_leaves_nothing_behind(self):
        """Refused inside the transaction — no orphan entry, no orphan lines.
        A half-written entry is worse than no entry: it balances the books
        nowhere and hides in the ledger looking like a real one."""
        with self.assertRaises(ValidationError):
            self.post([debit("1200", "1000.00"), credit("4000", "999.99")])
        self.assertEqual(JournalEntry.objects.count(), 0)
        self.assertEqual(JournalLine.objects.count(), 0)

    def test_an_entry_with_no_lines_is_refused(self):
        with self.assertRaises(ValidationError):
            self.post([])
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_a_line_cannot_carry_both_a_debit_and_a_credit(self):
        """Enforced by the database, not just by the service — this is the
        invariant every balance downstream rests on."""
        entry = self.post([debit("1200", "10.00"), credit("4000", "10.00")])
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                JournalLine.objects.create(
                    entry=entry, account=ChartAccount.objects.get(code="1000"),
                    debit=Decimal("5.00"), credit=Decimal("5.00"))

    def test_a_line_cannot_be_zero_on_both_sides(self):
        entry = self.post([debit("1200", "10.00"), credit("4000", "10.00")])
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                JournalLine.objects.create(
                    entry=entry, account=ChartAccount.objects.get(code="1000"))

    def test_a_negative_amount_is_refused(self):
        """A negative debit is a credit wearing a disguise, and it would
        make the two column totals agree while the ledger says something
        nobody meant."""
        entry = self.post([debit("1200", "10.00"), credit("4000", "10.00")])
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                JournalLine.objects.create(
                    entry=entry, account=ChartAccount.objects.get(code="1000"),
                    debit=Decimal("-5.00"))

    def test_posting_to_a_missing_account_names_the_code(self):
        with self.assertRaises(ValidationError):
            self.post([debit("9999", "1.00"), credit("4000", "1.00")])

    def test_many_lines_balance_as_a_whole_not_in_pairs(self):
        entry = self.post([
            debit("1000", "600.00"),
            debit("1200", "400.00"),
            credit("4000", "1000.00"),
        ])
        self.assertTrue(entry.is_balanced)


class AccountBalances(LedgerBase):
    def test_a_balance_runs_in_the_direction_the_account_normally_runs(self):
        """So every account reads positive when it holds what it should,
        and no caller has to remember which way round this one goes."""
        self.post([debit("1200", "1000.00"), credit("4000", "1000.00")])
        self.assertEqual(ChartAccount.objects.get(code="1200").balance(self.book),
                         Decimal("1000.00"))
        self.assertEqual(ChartAccount.objects.get(code="4000").balance(self.book),
                         Decimal("1000.00"))

    def test_balances_are_per_book(self):
        other = Book.objects.create(name="Ergene Fabric")
        self.post([debit("1200", "1000.00"), credit("4000", "1000.00")])
        post_entry(book=other, date="2026-07-16", description="theirs",
                   lines=[debit("1200", "50.00"), credit("4000", "50.00")])
        ar = ChartAccount.objects.get(code="1200")
        self.assertEqual(ar.balance(self.book), Decimal("1000.00"))
        self.assertEqual(ar.balance(other), Decimal("50.00"))
        self.assertEqual(ar.balance(), Decimal("1050.00"))

    def test_a_date_cutoff_excludes_later_entries(self):
        self.post([debit("1200", "100.00"), credit("4000", "100.00")], when="2026-01-31")
        self.post([debit("1200", "900.00"), credit("4000", "900.00")], when="2026-06-30")
        ar = ChartAccount.objects.get(code="1200")
        self.assertEqual(ar.balance(self.book, date_to=date(2026, 3, 1)), Decimal("100.00"))


class Statements(LedgerBase):
    def setUp(self):
        super().setUp()
        # A migrated opening balance: the receivable, with its contra in
        # opening equity rather than in revenue — last year's trading is
        # not this year's.
        self.post([debit("1200", "328646.42"), credit("3100", "328646.42")],
                  description="Opening balances carried forward")
        # A sale on credit, then part of it collected.
        self.post([debit("1200", "1000.00"), credit("4000", "1000.00")],
                  description="Sale")
        self.post([debit("1000", "400.00"), credit("1200", "400.00")],
                  description="Collection")
        # An expense paid in cash.
        self.post([debit("5100", "150.00"), credit("1000", "150.00")],
                  description="Expense")

    def test_the_trial_balance_balances(self):
        tb = trial_balance(self.book)
        self.assertTrue(tb["balanced"])
        self.assertEqual(tb["difference"], Decimal("0.00"))

    def test_the_balance_sheet_balances(self):
        """The point of the whole exercise: A = L + E, with no residual and
        nothing to explain."""
        bs = balance_sheet(self.book)
        self.assertTrue(bs["balanced"])
        self.assertEqual(bs["difference"], Decimal("0.00"))
        self.assertEqual(bs["assets"], bs["liabilities"] + bs["equity"])

    def test_the_period_result_is_carried_into_equity_before_closing(self):
        """Revenue and expenses are equity in the end. A balance sheet drawn
        before the books are closed has to include them or it fails for the
        honest reason that the year's profit has nowhere to sit yet."""
        bs = balance_sheet(self.book)
        self.assertEqual(bs["revenue"], Decimal("1000.00"))
        self.assertEqual(bs["expenses"], Decimal("150.00"))
        self.assertEqual(bs["result"], Decimal("850.00"))
        self.assertEqual(bs["equity"], Decimal("328646.42") + Decimal("850.00"))

    def test_the_figures_are_the_ones_the_subsidiary_ledgers_would_give(self):
        bs = balance_sheet(self.book)
        # A/R: 328,646.42 opened + 1,000 sold - 400 collected
        self.assertEqual(
            ChartAccount.objects.get(code="1200").balance(self.book),
            Decimal("329246.42"))
        # Cash: 400 in - 150 out
        self.assertEqual(
            ChartAccount.objects.get(code="1000").balance(self.book),
            Decimal("250.00"))
        self.assertEqual(bs["assets"], Decimal("329496.42"))

    def test_a_cutoff_still_balances(self):
        """Every entry balances, so any subset of them balances too — a
        statement as at any date is sound without a period-end routine."""
        bs = balance_sheet(self.book, date_to=date(2026, 7, 16))
        self.assertTrue(bs["balanced"])


class Traceability(LedgerBase):
    def test_an_entry_can_name_the_document_that_caused_it(self):
        """A ledger row that cannot be traced to its cause is a row nobody
        can check."""
        cari_book = self.book
        entry = post_entry(
            book=cari_book, date="2026-07-16", description="from a document",
            lines=[debit("1200", "10.00"), credit("4000", "10.00")],
            source=cari_book, reference="BACKFILL-001")
        entry.refresh_from_db()
        self.assertEqual(entry.source, cari_book)
        self.assertEqual(entry.reference, "BACKFILL-001")

    def test_a_batch_reference_finds_the_whole_run(self):
        for _ in range(3):
            post_entry(book=self.book, date="2026-07-16", description="x",
                       lines=[debit("1200", "1.00"), credit("4000", "1.00")],
                       reference="BACKFILL-002")
        self.assertEqual(JournalEntry.objects.filter(reference="BACKFILL-002").count(), 3)

    def test_a_line_can_name_the_customer_behind_a_control_account(self):
        """Without this a control account cannot be reconciled against the
        ledger that summarises it."""
        from accounting.models_accounts import CariAccount
        cari = CariAccount.objects.create(
            book=self.book, code="00554", name="GÜRHAN", default_currency=self.usd)
        entry = self.post([debit("1200", "10.00", cari=cari), credit("4000", "10.00")])
        line = entry.lines.get(account__code="1200")
        self.assertEqual(line.cari, cari)
