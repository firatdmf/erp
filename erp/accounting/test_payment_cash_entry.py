# to run this test, use the command:
# python manage.py test accounting.test_payment_cash_entry

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from accounting.models import (
    Book,
    CashAccount,
    CashTransactionEntry,
    CurrencyCategory,
)
from accounting.models_accounts import CariAccount, Payment


class PaymentCashEntryTest(TestCase):
    """A payment that moves cash must leave a row in the cash ledger.

    It writes straight to CashAccount.balance, and used to record nothing
    in CashTransactionEntry — so the balance moved while the transactions
    page showed nothing, and its running total counted nothing. Linking a
    cash account to an already-confirmed payment was the plainest case:
    the money appeared in the account, the row never did.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="entry_tester", password="pw"
        )
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$"
        )
        self.book = Book.objects.create(name="Laleli Fabric")
        self.cash = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd, balance=Decimal("1000.00")
        )
        self.vault = CashAccount.objects.create(
            book=self.book, name="Vault", currency=self.usd, balance=Decimal("0.00")
        )
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-001", name="Maria", type="customer",
            default_currency=self.usd,
        )

    def _payment(self, cash_account=None, amount="400.00", ptype="collection"):
        return Payment.objects.create(
            cari=self.cari, book=self.book, number=f"PAY-{ptype}-1",
            type=ptype, method="cash", status="draft",
            date=timezone.localdate(),
            amount=Decimal(amount), currency=self.usd,
            cash_account=cash_account,
        )

    def _entries(self, payment):
        return CashTransactionEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(Payment),
            content_pk=payment.pk,
        )

    # -- confirming --------------------------------------------------------
    def test_confirming_writes_the_cash_entry(self):
        payment = self._payment(cash_account=self.cash)
        payment.confirm(user=self.user)

        entry = self._entries(payment).get()
        self.assertEqual(entry.amount, Decimal("400.00"))
        self.assertTrue(entry.is_amount_positive)
        self.assertEqual(entry.cash_account_id, self.cash.pk)
        self.assertEqual(entry.date, payment.date)
        # Stamped after the balance moved: 1000 + 400.
        self.assertEqual(entry.cash_account_balance, Decimal("1400.00"))

    def test_a_payment_out_is_recorded_as_money_leaving(self):
        payment = self._payment(cash_account=self.cash, ptype="payment")
        payment.confirm(user=self.user)

        entry = self._entries(payment).get()
        self.assertFalse(entry.is_amount_positive)
        self.assertEqual(entry.cash_account_balance, Decimal("600.00"))

    def test_confirming_without_a_cash_account_writes_nothing(self):
        """No cash account means no cash moved — there is nothing to record."""
        payment = self._payment(cash_account=None)
        payment.confirm(user=self.user)
        self.assertEqual(self._entries(payment).count(), 0)

    # -- editing -----------------------------------------------------------
    def test_linking_an_account_afterwards_writes_the_entry(self):
        """The reported bug: payment 79, linked after the fact."""
        payment = self._payment(cash_account=None)
        payment.confirm(user=self.user)
        self.assertEqual(self._entries(payment).count(), 0)

        # What the edit view does: shift the balance, then sync.
        CashAccount.objects.filter(pk=self.cash.pk).update(
            balance=Decimal("1000.00") + Decimal("400.00")
        )
        payment.cash_account = self.cash
        payment.save(update_fields=["cash_account"])
        payment.sync_cash_entry()

        entry = self._entries(payment).get()
        self.assertEqual(entry.cash_account_id, self.cash.pk)
        self.assertEqual(entry.amount, Decimal("400.00"))

    def test_editing_updates_in_place_rather_than_adding_a_row(self):
        payment = self._payment(cash_account=self.cash)
        payment.confirm(user=self.user)
        first = self._entries(payment).get().pk

        payment.amount = Decimal("650.00")
        payment.cash_account = self.vault
        payment.save(update_fields=["amount", "cash_account"])
        payment.sync_cash_entry()

        entry = self._entries(payment).get()  # still exactly one
        self.assertEqual(entry.pk, first)
        self.assertEqual(entry.amount, Decimal("650.00"))
        self.assertEqual(entry.cash_account_id, self.vault.pk)

    def test_unlinking_the_account_removes_the_entry(self):
        payment = self._payment(cash_account=self.cash)
        payment.confirm(user=self.user)
        self.assertEqual(self._entries(payment).count(), 1)

        payment.cash_account = None
        payment.save(update_fields=["cash_account"])
        payment.sync_cash_entry()
        self.assertEqual(self._entries(payment).count(), 0)

    # -- cancelling --------------------------------------------------------
    def test_cancelling_removes_the_entry(self):
        payment = self._payment(cash_account=self.cash)
        payment.confirm(user=self.user)
        self.assertEqual(self._entries(payment).count(), 1)

        payment.cancel(user=self.user)
        self.assertEqual(self._entries(payment).count(), 0)

    def test_the_ledger_still_sums_to_the_account_after_a_cancel(self):
        """The invariant repair_cash_running_balance checks."""
        payment = self._payment(cash_account=self.cash)
        payment.confirm(user=self.user)
        payment.cancel(user=self.user)

        self.cash.refresh_from_db()
        self.assertEqual(self.cash.balance, Decimal("1000.00"))
        self.assertEqual(self._entries(payment).count(), 0)

    def test_syncing_twice_does_not_duplicate(self):
        payment = self._payment(cash_account=self.cash)
        payment.confirm(user=self.user)
        payment.sync_cash_entry()
        payment.sync_cash_entry()
        self.assertEqual(self._entries(payment).count(), 1)
