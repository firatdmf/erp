"""A transfer between two accounts posts as one entry, inside Accounts
Receivable, and parks nothing in Suspense.

Run with:
    python manage.py test accounting.tests.test_account_transfer_posting
"""
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import (CurrentAccount, CurrentAccountMovement,
                                        CurrentAccountTransfer)
from accounting.models_ledger import JournalEntry, JournalLine
from accounting.services_ledger import ensure_chart


class AccountTransferPosting(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        ensure_chart()
        self.valentina = CurrentAccount.objects.create(
            book=self.book, code="2615", name="VALENTINA", type="customer",
            default_currency=self.usd)
        self.adem = CurrentAccount.objects.create(
            book=self.book, code="00286", name="ADEM", type="customer",
            default_currency=self.usd)
        CurrentAccountMovement.objects.create(
            current_account=self.valentina, book=self.book, date="2026-10-01",
            amount=Decimal("1000.00"), currency=self.usd, movement_type="opening")

    def _transfer(self, amount="325.64"):
        transfer = CurrentAccountTransfer.objects.create(
            book=self.book, date="2026-10-08", from_current_account=self.valentina,
            to_current_account=self.adem, amount=Decimal(amount), currency=self.usd,
            description="28800 rubles sent to Adem")
        transfer.post()
        return transfer

    def _entries(self, transfer):
        """Every entry the transfer or either of its legs is behind."""
        own = JournalEntry.objects.filter(
            source_type=ContentType.objects.get_for_model(CurrentAccountTransfer),
            source_id=transfer.pk)
        legs = JournalEntry.objects.filter(
            source_type=ContentType.objects.get_for_model(CurrentAccountMovement),
            source_id__in=[pk for pk in (transfer.from_movement_id, transfer.to_movement_id) if pk])
        return list(own), list(legs)

    def _balance(self, code, account=None):
        lines = JournalLine.objects.filter(entry__book=self.book, account__code=code)
        if account is not None:
            lines = lines.filter(current_account=account)
        totals = lines.aggregate(d=Sum("debit"), c=Sum("credit"))
        return (totals["d"] or 0) - (totals["c"] or 0)

    def test_it_is_one_entry_with_both_accounts_on_it(self):
        transfer = self._transfer()
        own, legs = self._entries(transfer)
        self.assertEqual(len(own), 1)
        self.assertEqual(legs, [])
        entry = own[0]
        self.assertEqual(entry.reference, transfer.reference)
        self.assertEqual(entry.description, "28800 rubles sent to Adem")
        lines = {(l.account.code, l.current_account.code): (l.debit, l.credit)
                 for l in entry.lines.select_related("account", "current_account")}
        self.assertEqual(lines, {
            ("1200", "00286"): (Decimal("325.64"), Decimal("0")),
            ("1200", "2615"): (Decimal("0"), Decimal("325.64")),
        })

    def test_nothing_touches_suspense(self):
        self._transfer()
        self.assertFalse(JournalLine.objects.filter(
            entry__book=self.book, account__code="1900").exists())

    def test_the_ledger_still_agrees_with_each_account(self):
        self._transfer()
        self.assertEqual(self._balance("1200"), Decimal("1000.00"))
        self.assertEqual(self._balance("1200", self.valentina), Decimal("674.36"))
        self.assertEqual(self._balance("1200", self.adem), Decimal("325.64"))

    def test_correcting_the_amount_leaves_one_entry_at_the_new_figure(self):
        transfer = self._transfer()
        transfer.amount = Decimal("400.00")
        transfer.save()
        transfer.repost()
        own, legs = self._entries(transfer)
        self.assertEqual(len(own), 1)
        self.assertEqual(legs, [])
        self.assertEqual(self._balance("1200", self.adem), Decimal("400.00"))
        self.assertEqual(self._balance("1200", self.valentina), Decimal("600.00"))
        self.assertEqual(self._balance("1900"), 0)

    def test_undoing_it_takes_the_entry_away(self):
        transfer = self._transfer()
        pk = transfer.pk
        transfer.unpost()
        transfer.delete()
        self.assertFalse(JournalEntry.objects.filter(
            source_type=ContentType.objects.get_for_model(CurrentAccountTransfer),
            source_id=pk).exists())
        self.assertEqual(self._balance("1200"), Decimal("1000.00"))
        self.assertEqual(self._balance("1200", self.adem), 0)
        self.assertEqual(self._balance("1900"), 0)

    def test_a_leg_changed_by_hand_is_posted_by_itself_again(self):
        """The pair no longer cancels, so it cannot be one entry inside
        Accounts Receivable; each leg says what it says and the difference
        waits in Suspense, as any adjustment's would."""
        transfer = self._transfer()
        leg = transfer.to_movement
        leg.amount = Decimal("300.00")
        leg.amount_base = Decimal("300.00")
        leg.save()
        own, legs = self._entries(transfer)
        self.assertEqual(own, [])
        self.assertEqual(len(legs), 2)
        self.assertEqual(self._balance("1200", self.adem), Decimal("300.00"))
        self.assertEqual(self._balance("1200", self.valentina), Decimal("674.36"))
        self.assertEqual(self._balance("1900"), Decimal("25.64"))

    def test_a_transfer_in_another_currency_cancels_in_the_books_currency(self):
        lira = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        transfer = CurrentAccountTransfer.objects.create(
            book=self.book, date="2026-10-08", from_current_account=self.valentina,
            to_current_account=self.adem, amount=Decimal("1000.00"), currency=lira,
            exchange_rate=Decimal("0.0203"))
        transfer.post()
        own, legs = self._entries(transfer)
        self.assertEqual(len(own), 1)
        self.assertEqual(legs, [])
        self.assertEqual(self._balance("1200", self.adem), Decimal("20.30"))
        self.assertEqual(self._balance("1900"), 0)
