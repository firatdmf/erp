# to run this test, use the command:
# python manage.py test accounting.test_invoice_no_marker

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounting.models import (
    Book, CariAccount, CariMovement, CurrencyCategory, Invoice, InvoiceItem,
)


class InvoiceMarkerBase(TestCase):
    """An invoice raised against an order posts nothing.

    It used to write a 0.00 row — the order_sale already carried the
    receivable, so posting the total again would double-count — which put
    lines on the statement that could never explain how the balance got
    from the row above to the row below. Eleven of the retail account's
    thirty-one rows were markers like that.

    A STANDALONE invoice is a different thing entirely and still posts:
    for a purchase receipt or an order-less sale, that movement IS the
    debt and nothing else creates it.
    """

    def setUp(self):
        from operating.models import Order, Product

        self.user = get_user_model().objects.create_user(
            username="invoice_tester", password="pw")
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-001", name="ACME",
            default_currency=self.usd)
        self.product = Product.objects.create(title="STAR BLACKOUT")
        self.order = Order.objects.create()

    def invoice(self, order=None, type="sales", total="500.00"):
        inv = Invoice.objects.create(
            cari=self.cari, book=self.book,
            number="INV-%s-%s" % (type, "ord" if order else "std"),
            type=type, status="draft", date="2026-08-27",
            due_date="2026-09-27", currency=self.usd, order=order)
        InvoiceItem.objects.create(
            invoice=inv, description="fabric",
            quantity=Decimal("1.000"), unit_price=Decimal(total), tax_rate=0)
        inv.recompute_totals(save=True)
        return inv

    def movements(self):
        return CariMovement.objects.filter(cari=self.cari)


class OrderAttachedInvoiceTest(InvoiceMarkerBase):

    def test_issuing_posts_no_ledger_row(self):
        inv = self.invoice(order=self.order)
        self.assertIsNone(inv.issue())
        self.assertEqual(self.movements().count(), 0)

    def test_it_is_still_issued(self):
        inv = self.invoice(order=self.order)
        inv.issue()
        inv.refresh_from_db()
        self.assertEqual(inv.status, "issued")
        self.assertIsNone(inv.posted_movement)

    def test_the_balance_is_untouched(self):
        inv = self.invoice(order=self.order)
        inv.issue()
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.cached_balance, Decimal("0.00"))

    def test_editing_it_does_not_resurrect_the_row(self):
        """resync's `mv is None` branch exists to repost a movement that
        went missing. Without a guard it would recreate exactly the row
        issue() stopped writing, on every edit."""
        inv = self.invoice(order=self.order)
        inv.issue()

        inv.recompute_totals(save=True)
        self.assertIsNone(inv.resync_posted_movement())
        self.assertEqual(self.movements().count(), 0)

    def test_cancelling_it_is_a_clean_no_op(self):
        inv = self.invoice(order=self.order)
        inv.issue()
        inv.cancel(reason="test")
        inv.refresh_from_db()
        self.assertEqual(inv.status, "cancelled")
        self.assertEqual(self.movements().count(), 0)
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.cached_balance, Decimal("0.00"))


class StandaloneInvoiceStillPostsTest(InvoiceMarkerBase):
    """The seven purchase receipts and two order-less sales in the books
    depend on this. Their movement is the debt."""

    def test_a_standalone_sale_posts_its_total(self):
        inv = self.invoice(order=None, total="500.00")
        mv = inv.issue()
        self.assertIsNotNone(mv)
        self.assertEqual(mv.amount, Decimal("500.00"))
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.cached_balance, Decimal("500.00"))

    def test_a_standalone_purchase_posts_the_payable(self):
        inv = self.invoice(order=None, type="purchase", total="419.58")
        mv = inv.issue()
        self.assertIsNotNone(mv)
        self.assertEqual(mv.amount, Decimal("-419.58"))
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.cached_balance, Decimal("-419.58"))

    def test_editing_a_standalone_one_still_refreshes_its_row(self):
        inv = self.invoice(order=None, total="500.00")
        mv = inv.issue()
        inv.items.update(unit_price=Decimal("600.00"))
        inv.items.first().save()
        inv.recompute_totals(save=True)
        inv.resync_posted_movement()

        mv.refresh_from_db()
        self.assertEqual(mv.amount, Decimal("600.00"))
        self.cari.refresh_from_db()
        self.assertEqual(self.cari.cached_balance, Decimal("600.00"))
