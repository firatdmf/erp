"""Saving the product page changes the variants it lists, and deletes only
the ones it says were removed.

The page used to list every combination of the option values and delete
whatever variant was not among them. A variant lacking an option the others
have matched no combination, so saving deleted it (or, when it had stock,
failed); and the combinations nobody makes were all created.

Run with:
    python manage.py test marketing.tests.test_variant_rows_save
"""
import json

from django.contrib.messages import get_messages
from django.contrib.messages.storage.cookie import CookieStorage
from django.test import RequestFactory, TestCase

from accounting.models import Book
from marketing.models import Product, ProductVariant
from marketing.views import ProductEdit
from operating.catalog_sync import set_variant_attributes, variant_attributes
from operating.models import Warehouse, WarehouseProduct


class VariantRowsSaveTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(title="K24614", sku="K24614", featured=True)
        self.white = self._variant("K24614.G28", [("color", "white"), ("width", "320")])
        self.gold = self._variant("K24614.G47", [("color", "gold"), ("width", "320")])
        # On another fabric, so no width: no combination of the options is it.
        self.velvet = self._variant("K24614.G99", [("color", "cream")])

    def _variant(self, sku, attributes):
        variant = ProductVariant.objects.create(product=self.product, variant_sku=sku)
        set_variant_attributes(variant, attributes, replace=True)
        return variant

    def _row(self, variant, **attrs):
        return {"variant_id": variant.pk, "variant_sku": variant.variant_sku,
                "variant_attribute_values": attrs, "variant_price": 10}

    def _save(self, rows, deleted=()):
        request = RequestFactory().post("/")
        request._messages = CookieStorage(request)
        view = ProductEdit()
        view.request, view.object = request, self.product
        view.handle_variants(self.product, json.dumps(
            {"product_variant_list": rows, "deleted_variant_ids": list(deleted), "deleted_files": []}))
        return [str(m) for m in get_messages(request)]

    def test_a_variant_the_page_leaves_out_is_kept_as_it_is(self):
        self._save([self._row(self.white, color="white", width="320"),
                    self._row(self.gold, color="gold", width="320")])
        self.velvet.refresh_from_db()
        self.assertEqual(variant_attributes(self.velvet), [("color", "cream")])

    def test_a_variant_without_an_option_is_saved_without_it(self):
        self._save([self._row(self.velvet, color="cream")])
        self.assertEqual(variant_attributes(self.velvet), [("color", "cream")])

    def test_the_variants_named_as_removed_are_deleted(self):
        self._save([self._row(self.white, color="white", width="320")], deleted=[self.gold.pk])
        self.assertFalse(ProductVariant.objects.filter(pk=self.gold.pk).exists())
        self.assertTrue(ProductVariant.objects.filter(pk=self.velvet.pk).exists())

    def test_one_with_stock_is_not_deleted_and_says_so(self):
        warehouse = Warehouse.objects.create(name="Laleli Fabrika", accounting_book=Book.objects.create(name="Laleli"))
        WarehouseProduct.objects.create(warehouse=warehouse, name="K24614 gold", sku="K24614.G47",
                                        catalog_variant=self.gold)
        said = self._save([self._row(self.white, color="white", width="320")], deleted=[self.gold.pk])
        self.assertTrue(ProductVariant.objects.filter(pk=self.gold.pk).exists())
        self.assertTrue(any("K24614.G47" in m for m in said), said)

    def test_a_new_row_becomes_a_new_variant(self):
        self._save([{"variant_id": "", "variant_sku": "K24614.G50",
                     "variant_attribute_values": {"color": "silver", "width": "320"}, "variant_price": 10}])
        made = ProductVariant.objects.get(variant_sku="K24614.G50")
        self.assertEqual(sorted(variant_attributes(made)), [("color", "silver"), ("width", "320")])
        self.assertEqual(self.product.variants.count(), 4)
