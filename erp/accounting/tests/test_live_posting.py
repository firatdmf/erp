"""The ledger keeps up with the books by itself.

Everything here creates records the ordinary way — objects.create, .save(),
.delete() — and then asks the general ledger what it knows. Nothing calls a
posting function directly, because the thing under test is precisely that
you do not have to.

Run with:
    python manage.py test accounting.tests.test_live_posting
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounting.models import Book, CashAccount, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.models_ledger import ChartAccount, JournalEntry
from accounting.services_ledger import balance_sheet, ensure_chart


class _Books(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        self.account = CurrentAccount.objects.create(
            book=self.book, code="00554", name="OLEG",
            default_currency=self.usd)

    def _mv(self, kind, amount, **extra):
        return CurrentAccountMovement.objects.create(
            current_account=self.account, book=self.book, date="2026-07-01",
            amount=Decimal(amount), currency=self.usd, movement_type=kind,
            description=kind, **extra)

    def _balances(self, book=None):
        return {r["code"]: r["balance"] for r in
                balance_sheet(book or self.book)["trial_balance"]["rows"]}


class SavingAMovementPostsIt(_Books):
    def test_a_new_movement_is_on_the_ledger_immediately(self):
        self._mv("order_sale", "167.75")
        b = self._balances()
        self.assertEqual(b["1200"], Decimal("167.75"))
        self.assertEqual(b["4000"], Decimal("167.75"))

    def test_the_entry_points_back_at_the_movement_that_caused_it(self):
        mv = self._mv("order_sale", "10.00")
        entry = JournalEntry.objects.get()
        self.assertEqual(entry.source, mv)
        self.assertEqual(entry.book, self.book)
        mv.refresh_from_db()
        self.assertEqual(entry.date, mv.date)

    def test_an_edit_moves_the_ledger_with_it(self):
        """The case a batch could never cover. resync_posted_movement
        re-saves the very same row when a payment's amount or rate is
        corrected; posting only when nothing was there yet would leave the
        ledger holding the figure that was corrected away."""
        mv = self._mv("order_sale", "100.00")
        mv.amount = Decimal("250.00")
        mv.amount_base = Decimal("250.00")
        mv.save()
        self.assertEqual(self._balances()["1200"], Decimal("250.00"))
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_voiding_withdraws_the_entry(self):
        mv = self._mv("order_sale", "400.00")
        mv.is_void = True
        mv.save()
        self.assertEqual(JournalEntry.objects.count(), 0)
        self.assertTrue(balance_sheet(self.book)["balanced"])

    def test_un_voiding_puts_it_back(self):
        mv = self._mv("order_sale", "400.00")
        mv.is_void = True
        mv.save()
        mv.is_void = False
        mv.save()
        self.assertEqual(self._balances()["1200"], Decimal("400.00"))
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_deleting_takes_the_entry_with_it(self):
        mv = self._mv("order_sale", "400.00")
        mv.delete()
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_an_adjustment_is_parked_rather_than_lost(self):
        """An undecided contra must not cost the ledger the row. 1200 has
        to equal what the accounts owe or it is not a control account."""
        self._mv("adjustment", "500.00")
        b = self._balances()
        self.assertEqual(b["1200"], Decimal("500.00"))
        self.assertEqual(b["1900"], Decimal("-500.00"))

    def test_the_equation_holds_through_a_run_of_ordinary_work(self):
        for kind, amount in (("opening", "1000.00"), ("order_sale", "250.00"),
                             ("collection", "-400.00"), ("adjustment", "35.50"),
                             ("invoice_purchase", "-600.00"),
                             ("interest", "12.00"), ("check_in", "-75.00")):
            self._mv(kind, amount)
        gl = balance_sheet(self.book)
        self.assertTrue(gl["balanced"])
        self.assertEqual(gl["assets"], gl["liabilities_plus_equity"])
        tb = gl["trial_balance"]
        self.assertEqual(tb["total_debit"], tb["total_credit"])


class PostingNeverBreaksTheBusinessWrite(_Books):
    """An operator recording a payment cannot answer a bookkeeping
    question, so a posting problem must cost the ledger an entry and never
    cost the business its record."""

    def test_a_missing_chart_heals_itself_rather_than_losing_the_posting(self):
        """Nobody has to have run a seed command first. A missing standard
        account used to mean a batch printed an error somebody read; live,
        it would mean every save quietly failed to post."""
        ChartAccount.objects.all().delete()
        mv = self._mv("order_sale", "500.00")
        self.assertTrue(CurrentAccountMovement.objects.filter(pk=mv.pk).exists())
        self.assertEqual(self._balances()["1200"], Decimal("500.00"))
        self.assertEqual(
            set(ChartAccount.objects.values_list("code", flat=True)),
            {"1200", "4000"})

    def test_a_type_with_no_rule_at_all_does_not_stop_the_save(self):
        mv = self._mv("order_sale", "500.00")
        mv.movement_type = "teleportation"
        with self.assertLogs("accounting.ledger", level="WARNING"):
            mv.save()
        # The save stood, and the entry it could not decide how to replace
        # was left exactly as it was rather than being deleted on the way
        # to failing.
        mv.refresh_from_db()
        self.assertEqual(mv.movement_type, "teleportation")
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_a_failed_repost_leaves_the_entry_it_was_replacing(self):
        """Reposting means withdrawing the old entry and writing a new one,
        and the withdrawal happens first. If the write then fails, the
        rollback has to take the withdrawal back with it — otherwise an
        edit nobody could post would quietly cost the ledger an entry it
        already had, and leave it short rather than stale."""
        from unittest.mock import patch

        from accounting import services_posting
        mv = self._mv("order_sale", "500.00")
        self.assertEqual(self._balances()["1200"], Decimal("500.00"))

        with patch.dict(services_posting.ALL_CONTRA_BY_TYPE,
                        {"order_sale": "8888"}):
            mv.amount = Decimal("900.00")
            mv.amount_base = Decimal("900.00")
            with self.assertLogs("accounting.ledger", level="WARNING"):
                mv.save()

        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertEqual(self._balances()["1200"], Decimal("500.00"))
        self.assertTrue(balance_sheet(self.book)["balanced"])

    def test_a_failure_leaves_nothing_half_written(self):
        """A rule naming an account outside the standard chart is a typo or
        a half-made decision, so it raises rather than inventing one. The
        entry then gets its first leg and cannot get its second — and
        because post_entry is atomic, the half-entry rolls back to its
        savepoint instead of standing as a one-sided row that would put the
        trial balance out by its own amount."""
        from unittest.mock import patch

        from accounting import services_posting
        with patch.dict(services_posting.ALL_CONTRA_BY_TYPE,
                        {"order_sale": "8888"}):
            with self.assertLogs("accounting.ledger", level="WARNING"):
                mv = self._mv("order_sale", "500.00")
        self.assertTrue(CurrentAccountMovement.objects.filter(pk=mv.pk).exists())
        self.assertEqual(JournalEntry.objects.count(), 0)
        self.assertEqual(
            ChartAccount.objects.filter(code="8888").count(), 0)


class TheInterCompanyMirrorPostsOnBothBooks(TestCase):
    def setUp(self):
        from accounting.services_mirror import pair_accounts

        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(
            name="Laleli Fabric", base_currency=self.usd)
        self.ergene = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        self.here = CurrentAccount.objects.create(
            book=self.laleli, code="L1", name="ERGENE",
            default_currency=self.usd)
        self.there = CurrentAccount.objects.create(
            book=self.ergene, code="E1", name="LALELI",
            default_currency=self.usd)
        pair_accounts(self.here, self.there)

    def _balances(self, book):
        return {r["code"]: r["balance"] for r in
                balance_sheet(book)["trial_balance"]["rows"]}

    def test_both_halves_post_to_their_own_book(self):
        CurrentAccountMovement.objects.create(
            current_account=self.here, book=self.laleli, date="2026-07-01",
            amount=Decimal("900.00"), currency=self.usd,
            movement_type="invoice_sale", description="fabric")

        here = self._balances(self.laleli)
        self.assertEqual(here["1200"], Decimal("900.00"))
        self.assertEqual(here["4000"], Decimal("900.00"))

        # The mirror is not a sale in the other book — no goods left
        # Ergene's shelves — so its contra is the clearing line, which says
        # the value is known and the reason is not.
        there = self._balances(self.ergene)
        self.assertEqual(there["1200"], Decimal("-900.00"))
        self.assertEqual(there["1950"], Decimal("900.00"))

    def test_each_book_balances_on_its_own(self):
        CurrentAccountMovement.objects.create(
            current_account=self.here, book=self.laleli, date="2026-07-01",
            amount=Decimal("900.00"), currency=self.usd,
            movement_type="invoice_sale", description="fabric")
        for book in (self.laleli, self.ergene):
            self.assertTrue(balance_sheet(book)["balanced"])

    def test_the_clearing_lines_are_equal_and_opposite(self):
        """A check nothing else in the system performs: if the pair is in
        step, the two clearing balances cancel across the group."""
        for amount, kind in (("900.00", "invoice_sale"),
                             ("-250.00", "collection"),
                             ("40.00", "interest")):
            CurrentAccountMovement.objects.create(
                current_account=self.here, book=self.laleli, date="2026-07-01",
                amount=Decimal(amount), currency=self.usd,
                movement_type=kind, description=kind)
        clearing = ChartAccount.objects.get(code="1950")
        self.assertEqual(clearing.balance(self.ergene), Decimal("690.00"))
        self.assertEqual(
            clearing.balance(self.laleli) + clearing.balance(self.ergene),
            # Laleli holds no clearing balance at all: its halves are real
            # events with real contras. The sum is the Ergene side alone,
            # which is what the pair has not yet explained.
            Decimal("690.00"))


class CashEventsPostAsTheyHappen(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(
            name="Ergene Fabric", base_currency=self.usd)
        ensure_chart()
        self.cash = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd)
        self.member = get_user_model().objects.create_user(
            "owner", password="pw").member

    def _cash_row(self, obj, amount, *, positive):
        from django.contrib.contenttypes.models import ContentType

        from accounting.models import CashTransactionEntry
        return CashTransactionEntry.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(obj.__class__),
            content_pk=obj.pk, amount=Decimal(amount),
            is_amount_positive=positive, currency=self.usd,
            cash_account=self.cash, date="2026-09-03")

    def _dividend(self, amount):
        from accounting.models import EquityDivident
        obj = EquityDivident.objects.create(
            book=self.book, cash_account=self.cash, currency=self.usd,
            amount=Decimal(amount), date="2026-09-03",
            description="Q3 distribution")
        return obj, self._cash_row(obj, amount, positive=False)

    def _balances(self):
        return {r["code"]: r["balance"] for r in
                balance_sheet(self.book)["trial_balance"]["rows"]}

    def test_a_dividend_posts_as_the_cash_row_is_written(self):
        self._dividend("1500.00")
        b = self._balances()
        self.assertEqual(b["3300"], Decimal("-1500.00"))
        self.assertEqual(b["1000"], Decimal("-1500.00"))

    def test_deleting_the_cash_row_withdraws_the_entry(self):
        _obj, row = self._dividend("1500.00")
        row.delete()
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_deleting_an_expense_the_way_the_app_does_withdraws_the_entry(self):
        """The app's own delete path drops the cash row first and the
        source second — see views.unpost_expense — so by the time anything
        looks for the object the entry names, it is already gone. The entry
        has to be found by the ids the row still carries, not by the
        object."""
        from accounting.models import EquityExpense, ExpenseCategory
        from accounting.views import unpost_expense

        category = ExpenseCategory.objects.create(name="Rent")
        expense = EquityExpense.objects.create(
            book=self.book, cash_account=self.cash, currency=self.usd,
            amount=Decimal("250.00"), date="2026-09-03",
            description="September rent", category=category)
        self._cash_row(expense, "250.00", positive=False)
        self.assertEqual(self._balances()["5100"], Decimal("250.00"))

        unpost_expense(expense)
        expense.delete()
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_a_confirmed_payment_posts_once_not_twice(self):
        """A Payment writes both a current-account movement and a cash row.
        The movement already carries the cash leg, so posting the row too
        would book the payment twice — and each entry would balance on its
        own, so nothing downstream would catch it.

        Driven through Payment.confirm(), which is what the payment form
        calls, so the two rows arrive exactly as they do in production."""
        from accounting.models import Payment

        account = CurrentAccount.objects.create(
            book=self.book, code="00554", name="OLEG",
            default_currency=self.usd)
        CurrentAccountMovement.objects.create(
            current_account=account, book=self.book, date="2026-09-03",
            amount=Decimal("-1000.00"), currency=self.usd,
            movement_type="invoice_purchase", description="fabric in")
        self.cash.balance = Decimal("5000.00")
        self.cash.save()

        payment = Payment.objects.create(
            current_account=account, book=self.book, number="PAY-1",
            type="payment", method="cash", status="draft", date="2026-09-03",
            amount=Decimal("300.00"), currency=self.usd,
            cash_account=self.cash)
        payment.confirm()

        # One entry for the purchase, one for the payment — and none for
        # the cash row the payment also wrote.
        self.assertEqual(JournalEntry.objects.count(), 2)
        b = self._balances()
        self.assertEqual(b["1000"], Decimal("-300.00"))   # cash went out
        self.assertEqual(b["1200"], Decimal("-700.00"))   # still owed
        self.assertTrue(balance_sheet(self.book)["balanced"])


class TheControlAccountsCanBeChecked(_Books):
    """A control account is only a control account if it can be checked
    against the ledger it summarises. Nothing checked them, which is how
    the books got $1.67M out without any single page being wrong."""

    def test_receivables_agree_with_the_sum_of_the_accounts(self):
        from accounting.services_ledger import reconcile

        second = CurrentAccount.objects.create(
            book=self.book, code="00555", name="AYŞE",
            default_currency=self.usd)
        self._mv("opening", "1000.00")
        self._mv("collection", "-250.00")
        CurrentAccountMovement.objects.create(
            current_account=second, book=self.book, date="2026-07-01",
            amount=Decimal("-400.00"), currency=self.usd,
            movement_type="opening", description="owed to them")
        for acc in (self.account, second):
            acc.recompute_balance(save=True)

        row = reconcile(self.book)["rows"][0]
        self.assertEqual(row["subsidiary"], Decimal("350.00"))
        self.assertEqual(row["ledger"], Decimal("350.00"))
        self.assertTrue(row["reconciled"])

    def test_it_still_agrees_after_the_payables_are_reclassified(self):
        """Every movement posts to 1200 whichever way the account ends up,
        and the reclass moves the credit balances to 2000 afterwards. The
        net is the figure to compare, before that entry and after it."""
        from accounting.services_posting import reclassify_payables
        from accounting.services_ledger import reconcile

        second = CurrentAccount.objects.create(
            book=self.book, code="00555", name="AYŞE",
            default_currency=self.usd)
        self._mv("opening", "1000.00")
        CurrentAccountMovement.objects.create(
            current_account=second, book=self.book, date="2026-07-01",
            amount=Decimal("-400.00"), currency=self.usd,
            movement_type="opening", description="owed to them")
        for acc in (self.account, second):
            acc.recompute_balance(save=True)

        reclassify_payables(self.book, date="2026-09-03")
        b = self._balances()
        self.assertEqual(b["1200"], Decimal("1000.00"))
        self.assertEqual(b["2000"], Decimal("400.00"))
        self.assertTrue(reconcile(self.book)["rows"][0]["reconciled"])

    def test_suspense_is_reported_as_work_outstanding(self):
        from accounting.services_ledger import reconcile

        self._mv("adjustment", "500.00")
        pending = {p["code"]: p["balance"] for p in reconcile(self.book)["pending"]}
        self.assertEqual(pending["1900"], Decimal("-500.00"))

    def test_an_entry_written_round_the_back_is_caught(self):
        """post_entry cannot write an unbalanced entry, so one that exists
        arrived another way — a hand-edited row, a restored dump, a
        migration writing lines directly."""
        from accounting.models_ledger import JournalLine
        from accounting.services_ledger import unbalanced_entries

        self._mv("order_sale", "500.00")
        self.assertEqual(unbalanced_entries(self.book), [])

        JournalLine.objects.filter(account__code="4000").update(
            credit=Decimal("400.00"))
        bad = unbalanced_entries(self.book)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["difference"], Decimal("100.00"))

    def test_the_audit_command_passes_on_a_sound_book(self):
        from io import StringIO

        from django.core.management import call_command

        self._mv("opening", "1000.00")
        self._mv("collection", "-250.00")
        self.account.recompute_balance(save=True)
        out = StringIO()
        call_command("audit_ledger", "--book", str(self.book.pk), stdout=out)
        self.assertIn("The ledger is sound.", out.getvalue())

    def test_the_audit_command_fails_on_an_unsound_one(self):
        from io import StringIO

        from django.core.management import call_command
        from django.core.management.base import CommandError

        from accounting.models_ledger import JournalLine

        self._mv("order_sale", "500.00")
        JournalLine.objects.filter(account__code="4000").update(
            credit=Decimal("400.00"))
        with self.assertRaises(CommandError):
            call_command("audit_ledger", "--book", str(self.book.pk),
                         stdout=StringIO())


class ReclassifyingAnAdjustment(_Books):
    """What the operator does from the movement's Edit screen: the row
    stays, only its type changes, and the ledger follows."""

    def test_a_forgiven_debt_becomes_a_bad_debt_expense(self):
        self._mv("opening", "271.81")
        adj = self._mv("adjustment", "-271.81")
        self.assertEqual(self._balances()["1900"], Decimal("271.81"))

        adj.movement_type = "write_off"
        adj.save()
        b = self._balances()
        self.assertNotIn("1900", b)                      # out of Suspense
        self.assertEqual(b["5200"], Decimal("271.81"))   # a loss, on its own line
        self.assertEqual(b["1200"], Decimal("0.00"))
        self.assertEqual(balance_sheet(self.book)["result"], Decimal("-271.81"))
        self.assertTrue(balance_sheet(self.book)["balanced"])
        self.assertEqual(JournalEntry.objects.count(), 2)

    def test_returned_goods_reverse_the_sale(self):
        self._mv("order_sale", "4471.05")
        adj = self._mv("adjustment", "-4471.05")
        adj.movement_type = "return_sale"
        adj.save()
        b = self._balances()
        self.assertNotIn("1900", b)
        self.assertEqual(b["4000"], Decimal("0.00"))
        self.assertEqual(b["1200"], Decimal("0.00"))

    def test_the_edit_screen_offers_the_new_type(self):
        from django.urls import reverse

        user = get_user_model().objects.create_user("acct", password="pw")
        user.member.books.set([self.book])
        user.member.default_book = self.book
        user.member.save(update_fields=["default_book"])
        self.client.force_login(user)
        adj = self._mv("adjustment", "-100.00")
        url = reverse("accounts:movement_edit",
                      kwargs={"pk": self.account.pk, "mv_pk": adj.pk})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'value="write_off"')


class TheFormPreviewsTheEntry(_Books):
    """The movement form draws the entry a row will write, so whoever
    types it can see both sides before saving."""

    def test_every_type_the_form_offers_has_a_rule_to_draw(self):
        from accounting.services_posting import posting_preview
        from accounting.views_accounts import _user_movement_choices

        rules = posting_preview()["rules"]
        for value, _label in _user_movement_choices():
            self.assertIn(value, rules, value)

    def test_it_names_the_other_side_and_flags_suspense(self):
        from accounting.services_posting import posting_preview

        preview = posting_preview()
        self.assertEqual(preview["control"]["code"], "1200")
        self.assertEqual(preview["rules"]["write_off"]["code"], "5200")
        self.assertEqual(preview["rules"]["write_off"]["name"], "Bad Debts Written Off")
        self.assertFalse(preview["rules"]["write_off"]["parked"])
        self.assertTrue(preview["rules"]["adjustment"]["parked"])

    def test_a_renamed_account_shows_by_its_new_name(self):
        from accounting.services_posting import posting_preview

        ChartAccount.objects.filter(code="4000").update(name="Kumaş Satışları")
        self.assertEqual(posting_preview()["rules"]["order_sale"]["name"],
                         "Kumaş Satışları")

    def test_the_new_movement_page_carries_the_preview(self):
        from django.urls import reverse

        user = get_user_model().objects.create_user("acct", password="pw")
        user.member.books.set([self.book])
        user.member.default_book = self.book
        user.member.save(update_fields=["default_book"])
        self.client.force_login(user)
        r = self.client.get(reverse("accounts:movement_create",
                                    kwargs={"pk": self.account.pk}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="mfPostingPreview"')
        self.assertContains(r, "What this does in the books")
