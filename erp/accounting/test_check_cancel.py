# to run this test, use the command:
# python manage.py test accounting.test_check_cancel

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import (
    CariAccount, CariMovement, CheckOrPromissoryNote,
)


class CheckCancelTest(TestCase):
    """Cancelling an instrument removes every ledger row it posted,
    rather than reversing each with a counter-movement. Matches
    Payment.cancel() and Invoice.cancel()."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="check_tester", password="pw"
        )
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.customer = CariAccount.objects.create(
            book=self.book, code="CARI-001", name="Maria", type="customer",
            default_currency=self.usd,
        )
        self.supplier = CariAccount.objects.create(
            book=self.book, code="CARI-002", name="Karven", type="supplier",
            default_currency=self.usd,
        )

    def _received_check(self, serial="CHK-001"):
        today = timezone.localdate()
        return CheckOrPromissoryNote.objects.create(
            book=self.book, cari=self.customer, instrument="check",
            direction="received", serial_no=serial,
            amount=Decimal("500.00"), currency=self.usd,
            issue_date=today, due_date=today,
        )

    def test_creating_posts_one_movement(self):
        self._received_check()
        self.assertEqual(self.customer.movements.count(), 1)

    def test_cancel_leaves_no_movement(self):
        check = self._received_check()
        check.cancel(user=self.user)

        self.assertEqual(self.customer.movements.count(), 0)
        check.refresh_from_db()
        self.assertEqual(check.status, "cancelled")
        self.assertIsNone(check.posted_movement_id)

    def test_cancel_does_not_post_a_counter_row(self):
        check = self._received_check()
        check.cancel(user=self.user)
        self.assertFalse(
            CariMovement.objects.filter(reference__startswith="CANCEL").exists()
        )

    def test_cancel_clears_the_endorsement_too(self):
        check = self._received_check()
        check.endorse(self.supplier, user=self.user)
        self.assertEqual(self.supplier.movements.count(), 1)

        check.cancel(user=self.user)

        self.assertEqual(self.customer.movements.count(), 0)
        self.assertEqual(self.supplier.movements.count(), 0)
        check.refresh_from_db()
        self.assertIsNone(check.endorse_movement_id)

    def test_cancel_clears_a_bounce_row(self):
        check = self._received_check()
        check.bounce(user=self.user, reason="insufficient funds")
        self.assertEqual(self.customer.movements.count(), 2)

        check.cancel(user=self.user)
        self.assertEqual(self.customer.movements.count(), 0)

    def test_cancel_restores_both_account_balances(self):
        before_customer = CariAccount.objects.get(pk=self.customer.pk).cached_balance
        before_supplier = CariAccount.objects.get(pk=self.supplier.pk).cached_balance

        check = self._received_check()
        check.endorse(self.supplier, user=self.user)
        self.assertNotEqual(
            CariAccount.objects.get(pk=self.customer.pk).cached_balance,
            before_customer)

        check.cancel(user=self.user)

        self.assertEqual(
            CariAccount.objects.get(pk=self.customer.pk).cached_balance,
            before_customer)
        self.assertEqual(
            CariAccount.objects.get(pk=self.supplier.pk).cached_balance,
            before_supplier)

    def test_cancel_is_idempotent(self):
        check = self._received_check()
        check.cancel(user=self.user)
        check.cancel(user=self.user)
        self.assertEqual(self.customer.movements.count(), 0)
