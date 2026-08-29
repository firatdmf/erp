# to run this test, use the command:
# python manage.py test accounting.test_supplier_promotion

from decimal import Decimal

from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount
from accounting.services_accounts import mark_as_supplier


class MarkAsSupplierTest(TestCase):
    """An account we have bought from is a supplier, and its type should say so.

    Buying does not stop someone being a customer — a mill that weaves for us
    and buys our seconds is both, which is why "both" is already a type and
    already has its own badge on the account page.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.n = 0

    def _cari(self, type_):
        self.n += 1
        return CariAccount.objects.create(
            book=self.book, code=f"CARI-{self.n:03d}", name=f"Account {self.n}",
            type=type_, default_currency=self.usd,
        )

    def test_a_customer_becomes_both_rather_than_stopping_being_a_customer(self):
        cari = self._cari("customer")
        self.assertTrue(mark_as_supplier(cari))
        cari.refresh_from_db()
        self.assertEqual(cari.type, "both")

    def test_an_account_that_is_neither_becomes_a_supplier(self):
        cari = self._cari("other")
        self.assertTrue(mark_as_supplier(cari))
        cari.refresh_from_db()
        self.assertEqual(cari.type, "supplier")

    def test_a_supplier_is_left_alone(self):
        cari = self._cari("supplier")
        self.assertFalse(mark_as_supplier(cari))
        cari.refresh_from_db()
        self.assertEqual(cari.type, "supplier")

    def test_both_is_left_alone(self):
        cari = self._cari("both")
        self.assertFalse(mark_as_supplier(cari))
        cari.refresh_from_db()
        self.assertEqual(cari.type, "both")

    def test_staff_is_left_alone(self):
        """A staff account settles expenses on the book's behalf. Turning a
        colleague into a vendor because one receipt was posted through them
        is a reclassification nobody asked for."""
        cari = self._cari("staff")
        self.assertFalse(mark_as_supplier(cari))
        cari.refresh_from_db()
        self.assertEqual(cari.type, "staff")

    def test_it_survives_being_called_twice(self):
        cari = self._cari("customer")
        mark_as_supplier(cari)
        self.assertFalse(mark_as_supplier(cari))
        cari.refresh_from_db()
        self.assertEqual(cari.type, "both")


class PurchaseInvoicePromotesTheAccountTest(TestCase):
    """The promotion has to happen where a purchase is actually recorded,
    not only where someone remembers to call it."""

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-900", name="Kızılırmak",
            type="customer", default_currency=self.usd,
        )

    def test_issuing_a_purchase_invoice_marks_the_account(self):
        from accounting.services_accounts import create_purchase_invoice_for_intake
        create_purchase_invoice_for_intake(
            self.cari,
            [{"description": "GREK Beyaz", "quantity": Decimal("50"), "unit": "mt",
              "unit_price": Decimal("2.00"), "currency": "USD"}],
        )
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.type, "both")
