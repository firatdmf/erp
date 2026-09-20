# to run this test, use the command:
# python manage.py test marketing.tests.test_supplier_item

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounting.models import Book, CurrencyCategory, CurrentAccount
from marketing.models import Product, ProductVariant, SupplierItem


class SupplierItemTests(TestCase):
    """One variant, two mills that each call it something else."""

    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Laleli Fabric", base_currency=usd)
        self.karven = CurrentAccount.objects.create(
            book=book, code="SUP-001", name="Karven", type="supplier",
            default_currency=usd)
        self.deneme = CurrentAccount.objects.create(
            book=book, code="SUP-002", name="Deneme", type="supplier",
            default_currency=usd)
        product = Product.objects.create(title="GREK TÜL", sku="N1464T")
        self.variant = ProductVariant.objects.create(
            product=product, variant_sku="N1464T-PETROL")
        self.other_variant = ProductVariant.objects.create(
            product=product, variant_sku="N1464T-EKRU")

    def link(self, account, sku, variant=None, **kw):
        return SupplierItem.objects.create(
            current_account=account, variant=variant or self.variant,
            supplier_sku=sku, **kw)

    def test_same_variant_from_two_suppliers(self):
        """The whole point: Product.supplier_account could only name one."""
        self.link(self.karven, "K24614", last_unit_price=Decimal("4.20"))
        self.link(self.deneme, "AB-4471", last_unit_price=Decimal("3.95"))

        sources = self.variant.supplier_items.order_by("last_unit_price")
        self.assertEqual(
            [(s.current_account.name, s.supplier_sku) for s in sources],
            [("Deneme", "AB-4471"), ("Karven", "K24614")],
        )

    def test_two_suppliers_may_reuse_the_same_digits(self):
        """Article numbers are only unique inside one supplier's catalog."""
        self.link(self.karven, "1001")
        self.link(self.deneme, "1001", variant=self.other_variant)
        self.assertEqual(SupplierItem.objects.filter(supplier_sku="1001").count(), 2)

    def test_one_supplier_sku_means_one_thing(self):
        """Their code pointing at two of our variants would make an
        incoming invoice line unresolvable."""
        self.link(self.karven, "K24614")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.link(self.karven, "K24614", variant=self.other_variant)

    def test_a_variant_is_listed_once_per_supplier(self):
        """Two rows would make "Karven's price for this" ambiguous."""
        self.link(self.karven, "K24614")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.link(self.karven, "K24614-OLD")

    def test_suppliers_without_barcodes_do_not_collide(self):
        """Most mills barcode at roll level and have no product GTIN at
        all, so the barcode column is mostly NULL — and NULLs must not
        count as duplicates of each other."""
        self.link(self.karven, "K24614")
        self.link(self.karven, "K24615", variant=self.other_variant)
        self.assertEqual(
            SupplierItem.objects.filter(supplier_barcode__isnull=True).count(), 2)

    def test_their_unit_is_restated_in_ours(self):
        """They sell a box of 12; we stock singles."""
        item = self.link(self.karven, "K24614", supplier_unit="box",
                         qty_per_supplier_unit=Decimal("12"))
        self.assertEqual(item.to_our_quantity(3), Decimal("36"))

    def test_quantity_per_unit_must_be_positive(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.link(self.karven, "K24614", qty_per_supplier_unit=Decimal("0"))
