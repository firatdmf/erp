# to run this test, use the command:
# python manage.py test accounting.test_payment_cancel

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounting.models import Book, CashAccount, CurrencyCategory
from accounting.models_accounts import CariAccount, CariMovement, Payment


class PaymentCancelTest(TestCase):
    """Cancelling a confirmed payment removes its ledger row rather than
    posting a counter-movement, so the statement shows one line and not
    two. Matches Invoice.cancel()."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cancel_tester", password="pw"
        )
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.cash = CashAccount.objects.create(
            book=self.book, name="Cash", currency=self.usd,
            balance=Decimal("1000.00"),
        )
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-001", name="Maria", type="customer",
            default_currency=self.usd,
        )

    def _confirmed_payment(self):
        payment = Payment.objects.create(
            cari=self.cari, book=self.book, number="COL-TEST-0001",
            type="collection", method="cash", status="draft",
            date=timezone.localdate(),
            amount=Decimal("400.00"), currency=self.usd,
            cash_account=self.cash,
        )
        payment.confirm(user=self.user)
        return payment

    def test_confirm_posts_one_movement(self):
        self._confirmed_payment()
        self.assertEqual(self.cari.movements.count(), 1)

    def test_cancel_leaves_no_movement(self):
        payment = self._confirmed_payment()
        payment.cancel(user=self.user)

        self.assertEqual(self.cari.movements.count(), 0)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "cancelled")
        self.assertIsNone(payment.posted_movement_id)

    def test_cancel_does_not_post_a_counter_row(self):
        payment = self._confirmed_payment()
        payment.cancel(user=self.user)
        self.assertFalse(
            CariMovement.objects.filter(description__startswith="CANCEL").exists()
        )

    def test_cancel_restores_the_cari_balance(self):
        before = CariAccount.objects.get(pk=self.cari.pk).cached_balance
        payment = self._confirmed_payment()
        self.assertNotEqual(
            CariAccount.objects.get(pk=self.cari.pk).cached_balance, before)

        payment.cancel(user=self.user)
        self.assertEqual(
            CariAccount.objects.get(pk=self.cari.pk).cached_balance, before)

    def test_cancel_reverses_the_cash_account(self):
        payment = self._confirmed_payment()
        self.assertEqual(
            CashAccount.objects.get(pk=self.cash.pk).balance, Decimal("1400.00"))

        payment.cancel(user=self.user)
        self.assertEqual(
            CashAccount.objects.get(pk=self.cash.pk).balance, Decimal("1000.00"))

    def test_cancel_is_idempotent(self):
        payment = self._confirmed_payment()
        payment.cancel(user=self.user)
        payment.cancel(user=self.user)

        self.assertEqual(self.cari.movements.count(), 0)
        self.assertEqual(
            CashAccount.objects.get(pk=self.cash.pk).balance, Decimal("1000.00"))

    def test_cancelling_a_draft_posts_and_reverses_nothing(self):
        payment = Payment.objects.create(
            cari=self.cari, book=self.book, number="COL-TEST-0002",
            type="collection", method="cash", status="draft",
            date=timezone.localdate(),
            amount=Decimal("50.00"), currency=self.usd, cash_account=self.cash,
        )
        payment.cancel(user=self.user)

        payment.refresh_from_db()
        self.assertEqual(payment.status, "cancelled")
        self.assertEqual(self.cari.movements.count(), 0)
        self.assertEqual(
            CashAccount.objects.get(pk=self.cash.pk).balance, Decimal("1000.00"))
