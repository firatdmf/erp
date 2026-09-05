# to run this test, use the command:
# python manage.py test accounting.test_retail_collections

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounting.models import Book, CariAccount, Payment
from accounting.services_accounts import (
    RETAIL_CARI_CODE,
    post_retail_order_financials,
    reverse_retail_order_financials,
)


class RetailPostingBase(TestCase):
    """Completing a retail order posts the sale and nothing else.

    It used to auto-collect the total as well, deciding what had already
    been collected by looking for payments tagged "ORD-<pk>" — a marker
    only it ever wrote. A collection entered by hand was invisible to it,
    so the whole total was taken a second time and the shared retail
    account ended up reading "we owe the customer".
    """

    def setUp(self):
        from accounting.models import CurrencyCategory
        from operating.models import Order, OrderItem, Product

        self.user = get_user_model().objects.create_user(
            username="retail_tester", password="pw")
        self.usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.product = Product.objects.create(title="STAR BLACKOUT")

        self.order = Order.objects.create(is_retail_order=True)
        OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=Decimal("5.60"), price=Decimal("10.18"))

    def retail_cari(self):
        return CariAccount.objects.filter(code=RETAIL_CARI_CODE).first()

    def collections(self):
        return Payment.objects.filter(
            cari=self.retail_cari(), type="collection", status="confirmed")


class RetailCompletionTest(RetailPostingBase):

    def test_completing_posts_the_sale(self):
        post_retail_order_financials(self.order, user=self.user)
        cari = self.retail_cari()
        self.assertIsNotNone(cari)
        self.assertEqual(cari.movements.filter(movement_type="order_sale").count(), 1)

    def test_completing_collects_nothing(self):
        """The whole point of the change — money is recorded by whoever
        took it, not invented on shipment."""
        post_retail_order_financials(self.order, user=self.user)
        self.assertEqual(self.collections().count(), 0)

    def test_the_sale_is_left_owing_until_someone_collects(self):
        """A deliberate consequence: the retail account no longer nets to
        zero on its own and carries a real receivable."""
        post_retail_order_financials(self.order, user=self.user)
        cari = self.retail_cari()
        cari.refresh_from_db()
        self.assertEqual(cari.cached_balance, Decimal("57.01"))

    def test_a_hand_entered_collection_is_not_duplicated(self):
        """The exact shape of the ORD-286 bug: a collection typed by a
        person, carrying no ORD tag, then the order completes."""
        post_retail_order_financials(self.order, user=self.user)
        cari = self.retail_cari()
        Payment.objects.create(
            cari=cari, book=cari.book, number="COL-MANUAL-1",
            type="collection", method="cash", status="draft",
            date="2026-08-27", amount=Decimal("57.00"), currency=self.usd,
            description="FIRATIN HESABINA GONDERDI",
        ).confirm()

        # Re-ship: this is where the second collection used to appear.
        post_retail_order_financials(self.order, user=self.user)

        self.assertEqual(self.collections().count(), 1)
        cari.refresh_from_db()
        self.assertEqual(cari.cached_balance, Decimal("0.01"))

    def test_completing_twice_posts_one_sale(self):
        post_retail_order_financials(self.order, user=self.user)
        post_retail_order_financials(self.order, user=self.user)
        cari = self.retail_cari()
        self.assertEqual(cari.movements.filter(movement_type="order_sale").count(), 1)
        cari.refresh_from_db()
        self.assertEqual(cari.cached_balance, Decimal("57.01"))


class RetailUnshipTest(RetailPostingBase):

    def test_unshipping_removes_the_sale(self):
        post_retail_order_financials(self.order, user=self.user)
        reverse_retail_order_financials(self.order, user=self.user)
        cari = self.retail_cari()
        self.assertEqual(cari.movements.filter(movement_type="order_sale").count(), 0)

    def test_unshipping_leaves_a_hand_entered_collection_alone(self):
        """Un-shipping an order does not un-receive money that actually
        changed hands."""
        post_retail_order_financials(self.order, user=self.user)
        cari = self.retail_cari()
        Payment.objects.create(
            cari=cari, book=cari.book, number="COL-MANUAL-2",
            type="collection", method="cash", status="draft",
            date="2026-08-27", amount=Decimal("57.01"), currency=self.usd,
            description="Müşteri ödedi",
        ).confirm()

        reverse_retail_order_financials(self.order, user=self.user)

        self.assertEqual(self.collections().count(), 1)

    def test_unshipping_still_cancels_a_historical_auto_collection(self):
        """Orders shipped before this change carry an AUTO collection, and
        un-shipping one must still reverse cleanly."""
        post_retail_order_financials(self.order, user=self.user)
        cari = self.retail_cari()
        Payment.objects.create(
            cari=cari, book=cari.book, number="COL-AUTO-1",
            type="collection", method="cash", status="draft",
            date="2026-08-27", amount=Decimal("57.01"), currency=self.usd,
            description="Retail automatic collection — Order #%d" % self.order.pk,
            notes="ORD-%d" % self.order.pk,
        ).confirm()

        reverse_retail_order_financials(self.order, user=self.user)

        self.assertEqual(self.collections().count(), 0)
        cari.refresh_from_db()
        self.assertEqual(cari.cached_balance, Decimal("0.00"))


class RetailReversalFindsTheOrdersOwnAccount(RetailPostingBase):
    """Un-shipping reverses against the account the order actually posted
    to, not against whichever book the acting member happens to work in.

    It used to look the retail cari up with
    `filter(book=get_default_book(), code=PERAKENDE)`. That is a guess,
    and when it guessed a book the account was not in it found nothing,
    reversed nothing, and left confirmed collections standing on an
    un-shipped order — silently, because "no account found" and "no
    collections to cancel" look identical from the outside.
    """

    def setUp(self):
        super().setUp()
        # A second book, and a member whose working book is that one —
        # the shape that made the guess wrong.
        self.other = Book.objects.create(name="Ergene Fabric")
        self.user.member.books.add(self.other)
        self.user.member.default_book = self.other
        self.user.member.save()

    def test_a_collection_is_reversed_from_another_book(self):
        post_retail_order_financials(self.order, user=self.user)
        cari = self.order.cari
        self.assertIsNotNone(cari)
        pay = Payment.objects.create(
            cari=cari, book=cari.book, number="TAH-TEST-1",
            type="collection", method="cash", status="draft",
            date=self.order.order_date or __import__("datetime").date.today(),
            amount=Decimal("10.00"), currency=self.usd,
            description="Retail automatic collection",
            notes=f"ORD-{self.order.pk}")
        pay.confirm(user=self.user)
        self.assertEqual(self.collections().count(), 1)

        reverse_retail_order_financials(self.order, user=self.user)
        self.assertEqual(self.collections().count(), 0)

    def test_the_sale_movement_is_reversed_too(self):
        post_retail_order_financials(self.order, user=self.user)
        cari = self.order.cari
        self.assertEqual(cari.movements.filter(movement_type="order_sale").count(), 1)
        reverse_retail_order_financials(self.order, user=self.user)
        self.assertEqual(cari.movements.filter(movement_type="order_sale").count(), 0)


class TheAutoCollectionPrefixMatchesWhatIsStored(RetailPostingBase):
    """The constant and the column have to say the same thing.

    reverse_retail_order_financials finds historical auto-collections by
    description prefix, so translating _RETAIL_AUTO_DESC without restating
    the rows would silently stop matching them — an un-shipped order would
    keep its confirmed collection and nobody would be told. Migration 0097
    moves the rows; this pins the two together.
    """

    def test_the_migration_and_the_constant_agree(self):
        import importlib
        mig = importlib.import_module(
            "accounting.migrations.0097_retail_auto_collection_desc_in_english")
        from accounting.services_accounts import _RETAIL_AUTO_DESC
        self.assertEqual(mig.EN_PREFIX, _RETAIL_AUTO_DESC)

    def test_a_restated_row_is_still_reversed(self):
        """The English description the migration leaves behind is the one
        the reversal has to find."""
        from accounting.services_accounts import _RETAIL_AUTO_DESC
        post_retail_order_financials(self.order, user=self.user)
        cari = self.retail_cari()
        Payment.objects.create(
            cari=cari, book=cari.book, number="COL-AUTO-EN",
            type="collection", method="cash", status="draft",
            date="2026-08-27", amount=Decimal("57.01"), currency=self.usd,
            description=f"{_RETAIL_AUTO_DESC} — Order #{self.order.pk}",
            notes="ORD-%d" % self.order.pk,
        ).confirm()

        reverse_retail_order_financials(self.order, user=self.user)

        self.assertEqual(self.collections().count(), 0)
        cari.refresh_from_db()
        self.assertEqual(cari.cached_balance, Decimal("0.00"))
