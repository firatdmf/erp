import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from marketing.models import Product, ProductVariant
from operating.catalog_sync import sync_roll_to_catalog
from operating.models import Warehouse, WarehouseProductItem


class VariantBarcodeFollowsTrackingTest(TestCase):
    """A variant barcode is the code on every piece of a product sold by
    count. A product tracked item by item labels each item instead, so its
    variants carry none — not even the first roll's label, which a receipt
    used to copy onto a new variant."""

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="track_tester", password="pw", email="t@r.k")
        self.client.force_login(self.user)
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Demfirat")
        self.account = CurrentAccount.objects.create(
            book=book, code="TST-KRV", name="Karven", type="supplier", default_currency=usd)
        self.warehouse = Warehouse.objects.create(name="Fabrika", accounting_book=book)

    def _receive(self, *, unit, tracking=None, barcode="", tops=None, mode="new", pid=None,
                 sku="TRK1.WHITE"):
        card = {
            "main_product": ({"mode": "existing", "id": pid} if mode == "existing"
                             else {"mode": "new", "name": "TRK1", "sku": "TRK1"}),
            "has_variants": True, "unit": unit,
            "variants": [{"attributes": [{"name": "color", "value": "white"}],
                          "sku": sku, "barcode": barcode,
                          "price": "3", "currency": "USD",
                          "tops": tops or [{"qty": 10}, {"qty": 12}]}],
        }
        if tracking:
            card["tracking"] = tracking
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({"current_account_id": self.account.pk, "unit": unit,
                             "products": [card]}),
            content_type="application/json")

    def test_rolls_get_labels_and_the_variant_none(self):
        r = self._receive(unit="m", barcode="8690000000017")
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(Product.objects.get(sku="TRK1").tracking, "item")
        rolls = WarehouseProductItem.objects.filter(product__warehouse=self.warehouse)
        self.assertEqual(rolls.count(), 2)
        self.assertTrue(all(r.barcode for r in rolls))
        self.assertIsNone(ProductVariant.objects.get(variant_sku="TRK1.WHITE").variant_barcode)

    def test_counted_goods_get_one_variant_barcode_and_no_item_labels(self):
        r = self._receive(unit="piece", barcode="8690000000017")
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(Product.objects.get(sku="TRK1").tracking, "variant")
        boxes = WarehouseProductItem.objects.filter(product__warehouse=self.warehouse)
        self.assertEqual(boxes.count(), 2)
        self.assertFalse(any(b.barcode for b in boxes))
        self.assertEqual(ProductVariant.objects.get(variant_sku="TRK1.WHITE").variant_barcode,
                         "8690000000017")

    def test_the_card_chooses_the_tracking_of_a_new_product(self):
        """Meters usually mean rolls, but the card's choice wins."""
        r = self._receive(unit="m", tracking="variant", barcode="8690000000017")
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(Product.objects.get(sku="TRK1").tracking, "variant")
        self.assertEqual(ProductVariant.objects.get(variant_sku="TRK1.WHITE").variant_barcode,
                         "8690000000017")

    def test_existing_product_with_stock_keeps_its_tracking(self):
        self._receive(unit="m")
        pid = Product.objects.get(sku="TRK1").pk
        r = self._receive(unit="m", tracking="variant", mode="existing", pid=pid)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(Product.objects.get(pk=pid).tracking, "item")

    def test_a_barcode_on_a_roll_is_refused_for_a_variant(self):
        self._receive(unit="m", tops=[{"qty": 10, "barcode": "ROLL-0001"}])
        counted = Product.objects.create(title="BOXES", sku="BOXES", unit="piece", featured=False,
                                         tracking="variant")
        r = self._receive(unit="piece", barcode="ROLL-0001", mode="existing",
                          pid=counted.pk, sku="BOXES.WHITE")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("ROLL-0001", r.json()["error"])

    def test_sync_drops_a_roll_label_for_an_item_tracked_product(self):
        product = Product.objects.create(title="ROLLS", sku="ROLLS", tracking="item")
        _p, v, _pc, _vc = sync_roll_to_catalog(
            base_name="ROLLS", attributes=[("color", "white")],
            variant_sku="ROLLS.WHITE", variant_barcode="KRV000123",
            existing_base_product=product)
        self.assertIsNone(v.variant_barcode)

        counted = Product.objects.create(title="BOXES", sku="BOXES", tracking="variant")
        _p, v, _pc, _vc = sync_roll_to_catalog(
            base_name="BOXES", attributes=[("color", "white")],
            variant_sku="BOXES.WHITE", variant_barcode="8690000000017",
            existing_base_product=counted)
        self.assertEqual(v.variant_barcode, "8690000000017")
