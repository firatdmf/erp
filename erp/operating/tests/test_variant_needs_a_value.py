"""Every variant says what it is: at least one attribute value.

PO 171 bought HAVANA with no colour and no width, so its variant was saved
as HAVANA.1 beside HAVANA.ECRU and nothing told the two apart. Now a
variant with no value is refused everywhere one is made or described: the
goods receipt, a draft purchase, the product page (a single item too), and
the catalog sync behind scans, imports and new warehouse rows. A variant
that already has values keeps them when a row names none.

Run with:
    python manage.py test operating.tests.test_variant_needs_a_value
"""
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from marketing.forms import _skus_without_values
from marketing.models import Product, ProductCategory, ProductVariant
from operating.catalog_sync import (UndescribedVariant, set_variant_attributes,
                                    sync_roll_to_catalog, variant_attributes)
from operating.models import Warehouse, WarehouseProduct


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn/qr.png")
class CatalogSyncRefusesTest(TestCase):
    def test_a_new_variant_with_no_value_is_refused_and_leaves_nothing(self, _up):
        with self.assertRaises(UndescribedVariant):
            sync_roll_to_catalog(base_name="HAVANA", variant_sku="HAVANA.1")
        self.assertFalse(ProductVariant.objects.exists())
        self.assertFalse(Product.objects.exists())

    def test_a_new_variant_with_a_value_is_made(self, _up):
        _p, variant, _pc, created = sync_roll_to_catalog(
            base_name="HAVANA", variant_sku="HAVANA.ECRU", attributes=[("color", "ecru")])
        self.assertTrue(created)
        self.assertEqual(variant_attributes(variant), [("color", "ecru")])

    def test_an_existing_variant_is_found_without_one(self, _up):
        _p, variant, _pc, _vc = sync_roll_to_catalog(
            base_name="HAVANA", variant_sku="HAVANA.ECRU", attributes=[("color", "ecru")])
        _p, again, _pc, created = sync_roll_to_catalog(base_name="HAVANA", variant_sku="HAVANA.ECRU")
        self.assertFalse(created)
        self.assertEqual(again.pk, variant.pk)
        self.assertEqual(variant_attributes(again), [("color", "ecru")])

    def _counted(self, **kw):
        return Product.objects.create(title="PREMIUM SATIN 300 TC", sku=None, featured=False,
                                      unit="piece", pack_type="loose",
                                      tracking=kw.get("tracking", "variant"))

    def test_counted_goods_named_by_their_printed_barcode_need_no_value(self, _up):
        # Almaty's shipments: twenty duvet designs under one name, told
        # apart by nothing but the EAN printed on each packet.
        product = self._counted()
        _p, variant, _pc, created = sync_roll_to_catalog(
            base_name=product.title, existing_base_product=product,
            variant_sku="8681910532267", variant_barcode="8681910532267")
        self.assertTrue(created)
        self.assertEqual(variant.product_id, product.pk)
        self.assertEqual(variant_attributes(variant), [])

    def test_found_by_title_the_barcode_names_it_too(self, _up):
        product = self._counted()
        _p, variant, _pc, created = sync_roll_to_catalog(
            base_name=product.title, variant_sku="8681910532205",
            variant_barcode="8681910532205")
        self.assertTrue(created)
        self.assertEqual(variant.product_id, product.pk)

    def test_counted_goods_without_a_barcode_still_need_a_value(self, _up):
        product = self._counted()
        with self.assertRaises(UndescribedVariant):
            sync_roll_to_catalog(base_name=product.title, existing_base_product=product,
                                 variant_sku="PREMIUM.1")
        self.assertFalse(ProductVariant.objects.exists())

    def test_goods_tracked_item_by_item_still_need_a_value(self, _up):
        # A roll's label names one roll, not the variant: HAVANA.1 again.
        product = self._counted(tracking="item")
        with self.assertRaises(UndescribedVariant):
            sync_roll_to_catalog(base_name=product.title, existing_base_product=product,
                                 variant_sku="HAVANA.1", variant_barcode="R-000123")
        self.assertFalse(ProductVariant.objects.exists())

    def test_a_new_product_with_a_barcode_still_needs_a_value(self, _up):
        # A main product made by the sync is a fabric, sold by the meter.
        with self.assertRaises(UndescribedVariant):
            sync_roll_to_catalog(base_name="NEW THING", variant_sku="8680000000001",
                                 variant_barcode="8680000000001")
        self.assertFalse(Product.objects.exists())

    def test_describing_a_variant_with_nothing_is_refused(self, _up):
        _p, variant, _pc, _vc = sync_roll_to_catalog(
            base_name="HAVANA", variant_sku="HAVANA.ECRU", attributes=[("color", "ecru")])
        with self.assertRaises(UndescribedVariant):
            set_variant_attributes(variant, [], replace=True)
        self.assertEqual(variant_attributes(variant), [("color", "ecru")])


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn/qr.png")
class GoodsReceiptRefusesTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("value_tester", "v@t.t", "pw")
        self.client.force_login(self.user)
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Laleli Fabric")
        self.account = CurrentAccount.objects.create(
            book=book, code="S-KZL", name="Kizilirmak", type="supplier", default_currency=usd)
        self.warehouse = Warehouse.objects.create(name="Fabrika", accounting_book=book)
        self.fabric = ProductCategory.objects.create(name="fabric")

    def _receive(self, variants, *, main=None, has_variants=True):
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({
                "current_account_id": self.account.pk,
                "products": [{
                    "main_product": main or {"mode": "new", "name": "HAVANA", "sku": "HAVANA"},
                    "category_id": self.fabric.pk, "unit": "m",
                    "has_variants": has_variants, "variants": variants,
                }],
            }), content_type="application/json")

    @staticmethod
    def _row(sku, *attrs, qty=50):
        return {"sku": sku, "price": "1", "currency": "USD", "tops": [{"qty": qty}],
                "attributes": [{"name": n, "value": v} for n, v in attrs]}

    def test_a_row_with_no_value_is_refused(self, _up):
        r = self._receive([self._row("", ("color", ""), ("width", ""))])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("undescribed", r.json())
        self.assertFalse(WarehouseProduct.objects.exists())
        self.assertFalse(ProductVariant.objects.exists())

    def test_a_row_with_one_value_is_received(self, _up):
        r = self._receive([self._row("", ("color", "ecru"), ("width", ""))])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(ProductVariant.objects.filter(variant_sku="HAVANA.ECRU").exists())

    def test_a_single_item_with_no_value_is_refused(self, _up):
        r = self._receive([self._row("")], has_variants=False)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("undescribed", r.json())

    def test_more_of_a_described_variant_needs_no_value_typed(self, _up):
        _p, variant, _pc, _vc = sync_roll_to_catalog(
            base_name="HAVANA", variant_sku="HAVANA.ECRU", attributes=[("color", "ecru")])
        main = {"mode": "existing", "id": variant.product_id, "name": "HAVANA"}
        r = self._receive([self._row("HAVANA.ECRU")], main=main)
        self.assertEqual(r.status_code, 200, r.content)


    def test_the_form_has_no_layout_for_a_card_without_attributes(self, _up):
        book = self.warehouse.accounting_book
        r = self.client.get(reverse("accounts:goods_receipt", kwargs={"book_id": book.pk}))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "np-no-variant")
        self.assertContains(r, "np-attr-needed")

    def test_every_card_reloads_as_rows_of_variants(self, _up):
        # The edit form never sends a card back as "the product itself":
        # every card is rows, each to carry a value.
        r = self._receive([self._row("", ("color", "ecru"))])
        self.assertEqual(r.status_code, 200, r.content)
        invoice_id = r.json()["purchase"]["invoice_id"]
        loaded = self.client.get(
            reverse("operating:warehouse_purchase_edit", args=[self.warehouse.pk, invoice_id]),
            headers={"x-requested-with": "XMLHttpRequest"}).json()
        self.assertTrue(all(card["has_variants"] for card in loaded["products"]))


class ProductPageRefusesTest(TestCase):
    def test_a_posted_variant_with_no_value_is_named(self):
        posted = json.dumps([
            {"variant_sku": "HAVANA.ECRU", "variant_attribute_values": {"color": "ecru"}},
            {"variant_sku": "HAVANA.1", "variant_attribute_values": {"color": "", "width": ""}},
        ])
        self.assertEqual(_skus_without_values(posted), {"HAVANA.1"})
