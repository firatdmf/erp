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


class NoBarcodeAboveTrackedItemsTest(TestCase):
    """Whatever writes it — a screen, a scan, a sheet — a product tracked
    item by item has no barcode on its variants or their warehouse rows."""

    def setUp(self):
        self.warehouse = Warehouse.objects.create(name="Fabrika", accounting_book=Book.objects.create(name="Demfirat"))
        self.rolls = Product.objects.create(title="ROLLS", sku="ROLLS", tracking="item")
        self.boxes = Product.objects.create(title="BOXES", sku="BOXES", unit="piece", tracking="variant")

    def _variant(self, product, sku, barcode):
        return ProductVariant.objects.create(product=product, variant_sku=sku, variant_barcode=barcode)

    def test_a_variant_of_rolls_drops_its_barcode(self):
        v = self._variant(self.rolls, "ROLLS.WHITE", "KRV000123")
        v.refresh_from_db()
        self.assertIsNone(v.variant_barcode)
        v.variant_barcode = "KRV000124"
        v.save(update_fields=["variant_cost"])
        v.refresh_from_db()
        self.assertIsNone(v.variant_barcode)

    def test_a_variant_sold_by_count_keeps_its_barcode(self):
        v = self._variant(self.boxes, "BOXES.WHITE", "8690000000017")
        v.refresh_from_db()
        self.assertEqual(v.variant_barcode, "8690000000017")

    def test_a_row_of_rolls_drops_its_barcode(self):
        from operating.models import WarehouseProduct
        v = self._variant(self.rolls, "ROLLS.WHITE", None)
        wp = WarehouseProduct.objects.create(warehouse=self.warehouse, name="r", sku=v.variant_sku,
                                             catalog_variant=v, barcode="KRV000123")
        wp.refresh_from_db()
        self.assertIsNone(wp.barcode)

    def test_switching_to_each_item_empties_what_it_carried(self):
        from operating.models import WarehouseProduct
        v = self._variant(self.boxes, "BOXES.WHITE", "8690000000017")
        wp = WarehouseProduct.objects.create(warehouse=self.warehouse, name="b", sku=v.variant_sku,
                                             catalog_variant=v, barcode="8690000000017")
        self.boxes.set_unit(tracking="item")
        v.refresh_from_db(); wp.refresh_from_db()
        self.assertIsNone(v.variant_barcode)
        self.assertIsNone(wp.barcode)


class SwitchingTrackingTest(TestCase):
    """Switching a product with stock between "by variant" and "each item".
    To each item: every item still in stock gets a barcode of its own, and
    the product page offers their labels. To by variant: the items keep
    their labels, and the edit page says which variants a scan can't find."""

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="switch_tester", password="pw", email="s@w.t")
        self.client.force_login(self.user)
        from operating.models import WarehouseProduct
        self.warehouse = Warehouse.objects.create(name="Fabrika", accounting_book=Book.objects.create(name="Demfirat"))
        self.product = Product.objects.create(title="BOXES", sku="BOXES", unit="piece", tracking="variant")
        self.variant = ProductVariant.objects.create(product=self.product, variant_sku="BOXES.WHITE",
                                                     variant_barcode="8690000000017")
        self.row = WarehouseProduct.objects.create(warehouse=self.warehouse, name="Boxes white",
                                                   sku="BOXES.WHITE", catalog_variant=self.variant)
        self.boxes = [WarehouseProductItem.objects.create(product=self.row, quantity=1, quantity_remaining=1)
                      for _ in range(2)]
        self.used_up = WarehouseProductItem.objects.create(product=self.row, quantity=1,
                                                           quantity_remaining=0, status="consumed")

    def test_each_item_labels_the_boxes_in_stock(self):
        self.product.set_unit(tracking="item")
        for box in self.boxes:
            box.refresh_from_db()
        codes = [b.barcode for b in self.boxes]
        self.assertTrue(all(codes))
        self.assertEqual(len(set(codes)), 2)
        self.used_up.refresh_from_db()
        self.assertIsNone(self.used_up.barcode)
        self.assertEqual(self.product.labelled_items, [(self.row, 2)])

    def test_new_codes_continue_the_rows_own_family(self):
        WarehouseProductItem.objects.create(product=self.row, quantity=1, quantity_remaining=1,
                                            barcode="KRV000041")
        self.product.set_unit(tracking="item")
        self.assertEqual(sorted(WarehouseProductItem.objects.filter(
            product=self.row, status="in_stock").values_list("barcode", flat=True)),
            ["KRV000041", "KRV000042", "KRV000043"])

    def test_by_variant_keeps_the_labels(self):
        self.product.set_unit(tracking="item")
        codes = sorted(WarehouseProductItem.objects.exclude(barcode=None).values_list("barcode", flat=True))
        self.product.set_unit(tracking="variant")
        self.assertEqual(self.product.labelled_items, ())
        self.assertEqual(sorted(WarehouseProductItem.objects.exclude(barcode=None)
                                .values_list("barcode", flat=True)), codes)

    def test_the_edit_page_says_what_a_switch_does(self):
        url = reverse("marketing:product_edit", args=[self.product.pk])
        switch = self.client.get(url).context["tracking_switch"]
        self.assertEqual(switch["to"], "item")
        self.assertIn("2 items in stock have no barcode", " ".join(switch["notes"]))
        self.assertIn("1 variant's barcode is cleared", " ".join(switch["notes"]))

        self.product.set_unit(tracking="item")
        switch = self.client.get(url).context["tracking_switch"]
        self.assertEqual(switch["to"], "variant")
        self.assertIn("1 variant has no barcode (BOXES.WHITE)", " ".join(switch["notes"]))

    def test_the_product_page_offers_the_new_labels_once(self):
        session = self.client.session
        session[f"labels_to_print_{self.product.pk}"] = [
            [self.warehouse.pk, self.row.pk, "Fabrika", "Boxes white", 2]]
        session.save()
        url = reverse("marketing:product_detail", args=[self.product.pk])
        label_url = reverse("operating:warehouse_product_label", args=[self.warehouse.pk, self.row.pk])
        self.assertContains(self.client.get(url), label_url)
        self.assertNotContains(self.client.get(url), label_url)
