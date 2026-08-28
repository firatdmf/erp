# to run this test, use the command:
# python manage.py test accounting.test_variant_sku_rename

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount, Invoice, InvoiceItem
from marketing.models import (
    Product, ProductVariant, ProductVariantAttribute, ProductVariantAttributeValue,
)
from operating.models import Order, OrderItem


class VariantSkuRenameReachesDocumentsTest(TestCase):
    """Renaming a catalog variant has to reach the paperwork that quotes it.

    An invoice line's description is a snapshot cut at invoicing time and it
    embeds the SKU. Renaming the variant used to leave every document still
    printing the dead code, so the invoice disagreed with the catalog and a
    search for the new SKU found none of the paperwork naming it.
    """

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-001", name="ZÜMRÜT", type="customer",
            default_currency=self.usd,
        )
        self.product = Product.objects.create(
            title="24861T YARIMAT ALTIN", sku="GEN005", featured=False)
        self.variant = ProductVariant.objects.create(
            product=self.product, variant_sku="GEN001-G77")
        attr = ProductVariantAttribute.objects.create(name="model")
        val = ProductVariantAttributeValue.objects.create(
            product_variant_attribute=attr, product_variant_attribute_value="g77")
        self.variant.product_variant_attribute_values.add(val)

        self.order = Order.objects.create()
        self.item = OrderItem.objects.create(
            order=self.order, product=self.product, product_variant=self.variant,
            quantity=Decimal("20.80"), price=Decimal("4.00"),
        )

    def _invoice(self, status="issued", earsiv_uuid="", number="INV-1"):
        inv = Invoice.objects.create(
            cari=self.cari, book=self.book, series="FAT", number=number,
            type="sales", status=status, date=date(2026, 8, 14),
            due_date=date(2026, 9, 14),
            currency=self.usd, earsiv_uuid=earsiv_uuid,
        )
        return InvoiceItem.objects.create(
            invoice=inv, line_no=1, product=self.product, variant=self.variant,
            order_item=self.item,
            description="24861T YARIMAT ALTIN — g77 [GEN001-G77]",
            quantity=Decimal("20.80"), unit="mt", unit_price=Decimal("4.00"),
        )

    def _rename(self, sku="K24861T.G77"):
        self.variant.variant_sku = sku
        self.variant.save(update_fields=["variant_sku"])

    def test_an_issued_invoice_line_is_re_rendered(self):
        row = self._invoice()
        self._rename()
        row.refresh_from_db()
        self.assertIn("[K24861T.G77]", row.description)
        self.assertNotIn("GEN001-G77", row.description)

    def test_a_cancelled_invoice_is_re_rendered_too(self):
        """Nothing was filed, and a cancelled document quoting a SKU that no
        longer exists is simply invisible to search."""
        row = self._invoice(status="cancelled", number="INV-2")
        self._rename()
        row.refresh_from_db()
        self.assertIn("[K24861T.G77]", row.description)

    def test_an_earsiv_filed_invoice_is_left_alone(self):
        """That document went to the tax authority; correcting it is a credit
        note, which is a human decision — the same rule sync_invoice_for_order
        already follows."""
        row = self._invoice(earsiv_uuid="abc-123", number="INV-3")
        self._rename()
        row.refresh_from_db()
        self.assertIn("[GEN001-G77]", row.description)

    def test_a_draft_is_left_alone(self):
        """issue() builds a draft's lines from the order later anyway."""
        row = self._invoice(status="draft", number="INV-4")
        self._rename()
        row.refresh_from_db()
        self.assertIn("[GEN001-G77]", row.description)

    def test_saving_a_variant_without_renaming_it_touches_nothing(self):
        row = self._invoice(number="INV-5")
        row.description = "hand-edited line text"
        row.save(update_fields=["description"])
        self.variant.variant_cost = Decimal("3.50")
        self.variant.save(update_fields=["variant_cost"])
        row.refresh_from_db()
        self.assertEqual(row.description, "hand-edited line text")

    def test_creating_a_variant_is_not_a_rename(self):
        ProductVariant.objects.create(product=self.product, variant_sku="K24861T.G99")
        self.assertEqual(
            InvoiceItem.objects.filter(description__contains="K24861T.G99").count(), 0)
