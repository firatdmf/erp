"""A variant is its SKU, described by as many attributes as it needs.

The goods-receipt form used to ask one free-text "Color / model" box and
guess: a colour name became `color`, anything else `model`, and a mill code
beside a colour ("V-106 KREM") kept only the colour. The save then folded a
new SKU into any variant sharing that colour, and a scan with a different
kind of attribute moved every other variant of the product onto it.

Now each row answers one field per attribute in its card's list (the
product group's preset, or what the product's variants carry), the catalog
matches on SKU alone, and a new variant the catalog couldn't tell apart from
an existing one is refused.

Run with:
    python manage.py test operating.tests.test_variant_attributes
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from marketing.attributes import normalize_attribute_name, normalize_attribute_value
from marketing.models import (CategoryVariantAttribute, Product, ProductCategory,
                              ProductVariant, ProductVariantAttribute,
                              ProductVariantAttributeValue)
from operating.catalog_sync import (LookAlikeVariant, sync_roll_to_catalog,
                                    variant_attributes)
from operating.models import Warehouse, WarehouseProduct


def _attrs(variant):
    return sorted(variant_attributes(variant))


class SpellingTest(SimpleTestCase):
    def test_names_are_lower_case_with_single_spaces(self):
        self.assertEqual(normalize_attribute_name("  Size  Per Panel "), "size per panel")

    def test_sizes_keep_the_storefronts_spelling(self):
        for typed in ("130x210", "130 X 210 cm", "130 x 210cm", "130×210 CM"):
            with self.subTest(typed=typed):
                self.assertEqual(normalize_attribute_value("size per panel", typed), "130 x 210 cm")

    def test_other_values_are_lower_case_with_underscores(self):
        self.assertEqual(normalize_attribute_value("model", "Rod Pocket"), "rod_pocket")

    def test_colors_are_spelled_the_american_way(self):
        self.assertEqual(normalize_attribute_value("color", "Light Grey"), "light_gray")
        self.assertEqual(normalize_attribute_value("model", "grey"), "grey")


class StoredSpellingTest(TestCase):
    def test_saving_applies_the_same_rule(self):
        size = ProductVariantAttribute.objects.create(name="Size Per Panel")
        self.assertEqual(size.name, "size per panel")
        value = ProductVariantAttributeValue.objects.create(
            product_variant_attribute=size, product_variant_attribute_value="130x240")
        self.assertEqual(value.product_variant_attribute_value, "130 x 240 cm")


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn/qr.png")
class CatalogSyncTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(title="K12137", sku="K12137", featured=False)

    def _sync(self, sku, attributes, **kw):
        return sync_roll_to_catalog(base_name="K12137", variant_sku=sku,
                                    attributes=attributes,
                                    existing_base_product=self.product, **kw)[1]

    def test_a_new_sku_is_a_new_variant_even_with_the_same_color(self, _up):
        """K12137.S11 and .S16 are both white; they are still two variants."""
        s11 = self._sync("K12137.S11", [("color", "white")])
        s16 = self._sync("K12137.S16", [("color", "white")])
        self.assertNotEqual(s11.pk, s16.pk)
        self.assertEqual(s16.variant_sku, "K12137.S16")

    def test_the_form_refuses_a_look_alike(self, _up):
        s11 = self._sync("K12137.S11", [("color", "white")])
        with self.assertRaises(LookAlikeVariant) as ctx:
            self._sync("K12137.S16", [("color", "WHITE")], refuse_lookalike=True)
        self.assertEqual(ctx.exception.variant, s11)
        self.assertFalse(ProductVariant.objects.filter(variant_sku="K12137.S16").exists())

    def test_every_attribute_is_kept(self, _up):
        v = self._sync("K12137.S11", [("model", "S11"), ("color", "Beyaz ")])
        self.assertEqual(_attrs(v), [("color", "beyaz"), ("model", "s11")])

    def test_resyncing_one_attribute_leaves_the_others(self, _up):
        v = self._sync("K12137.S11", [("model", "S11"), ("color", "white")])
        self._sync("K12137.S11", [("color", "cream")])
        self.assertEqual(_attrs(v), [("color", "cream"), ("model", "s11")])

    def test_other_variants_are_never_rewired(self, _up):
        """A scan used to move every variant of the product onto its own
        kind of attribute: one colour scan turned all models into colours."""
        coded = self._sync("K12137.S11", [("model", "S11")])
        self._sync("K12137.S16", [("color", "white")])
        self.assertEqual(_attrs(coded), [("model", "s11")])


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://cdn/qr.png")
class GoodsReceiptAttributesTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("attr_tester", "a@t.t", "pw")
        self.client.force_login(self.user)
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        book = Book.objects.create(name="Laleli Fabric")
        self.account = CurrentAccount.objects.create(
            book=book, code="S-KRV", name="Karven", type="supplier", default_currency=usd)
        self.warehouse = Warehouse.objects.create(name="Fabrika", accounting_book=book)
        self.fabric = ProductCategory.objects.create(name="fabric")

    def _receive(self, variants, main=None, category=None):
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({
                "current_account_id": self.account.pk,
                "products": [{
                    "main_product": main or {"mode": "new", "name": "K24644", "sku": "K24644"},
                    "category_id": (category or self.fabric).pk,
                    "unit": "mt", "has_variants": True,
                    "variants": variants,
                }],
            }), content_type="application/json")

    @staticmethod
    def _row(sku, *attrs, qty=10):
        return {"sku": sku, "price": "3", "currency": "USD", "tops": [{"qty": qty}],
                "attributes": [{"name": n, "value": v} for n, v in attrs]}

    def test_each_field_is_its_own_attribute(self, _up):
        r = self._receive([self._row("K24644.V106", ("color", "KREM"), ("model", "V-106"))])
        self.assertEqual(r.status_code, 200, r.content)
        variant = ProductVariant.objects.get(variant_sku="K24644.V106")
        # KREM is a colour and is stored by its English key; the code is kept.
        self.assertEqual(_attrs(variant), [("color", "cream"), ("model", "v-106")])
        # The warehouse row reads as typed.
        self.assertEqual(WarehouseProduct.objects.get().name, "K24644 KREM V-106")

    def test_a_row_from_before_the_fields_still_saves(self, _up):
        r = self._receive([{"name": "V-107", "sku": "K24644.V107", "price": "3",
                            "currency": "USD", "tops": [{"qty": 5}]}])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(_attrs(ProductVariant.objects.get(variant_sku="K24644.V107")),
                         [("model", "v-107")])

    def test_an_auto_sku_is_built_from_the_values(self, _up):
        r = self._receive([self._row("", ("model", "S11"), ("color", "white"))])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(ProductVariant.objects.filter(variant_sku="K24644.S11-WHITE").exists())

    def test_two_rows_with_the_same_values_are_refused(self, _up):
        r = self._receive([self._row("K24644.A", ("color", "white")),
                           self._row("K24644.B", ("color", "WHITE"))])
        self.assertEqual(r.status_code, 400)
        self.assertIn("lookalikes", r.json())
        self.assertFalse(WarehouseProduct.objects.exists())

    def test_a_new_sku_like_an_existing_variant_is_refused(self, _up):
        self._receive([self._row("K24644.S11", ("color", "white"))])
        product = Product.objects.get(sku="K24644")
        r = self._receive([self._row("K24644.S16", ("color", "white"))],
                          main={"mode": "existing", "id": product.pk})
        self.assertEqual(r.status_code, 400)
        self.assertIn("K24644.S11", r.json()["error"])
        self.assertFalse(ProductVariant.objects.filter(variant_sku="K24644.S16").exists())

    def test_look_alikes_already_in_the_catalog_still_take_stock(self, _up):
        """66 products already carry variants with equal values; receiving
        more of one of them must not be refused for it."""
        self._receive([self._row("K24644.S11", ("color", "white"))])
        product = Product.objects.get(sku="K24644")
        twin = ProductVariant.objects.create(product=product, variant_sku="K24644.S16")
        twin.product_variant_attribute_values.add(
            ProductVariantAttributeValue.objects.get(product_variant_attribute_value="white"))
        r = self._receive([self._row("K24644.S11", ("color", "white"), qty=7)],
                          main={"mode": "existing", "id": product.pk})
        self.assertEqual(r.status_code, 200, r.content)

    def test_the_match_endpoint_names_the_look_alike(self, _up):
        self._receive([self._row("K24644.S11", ("color", "white"))])
        product = Product.objects.get(sku="K24644")
        url = reverse("operating:catalog_variant_match", args=[self.warehouse.pk, product.pk])
        d = self.client.get(url, {"sku": "K24644.S16",
                                  "attrs": json.dumps([{"name": "color", "value": "BEYAZ"}])}).json()
        self.assertEqual((d.get("lookalike"), d["variant_sku"]), (True, "K24644.S11"))
        d = self.client.get(url, {"sku": "K24644.S11", "attrs": "[]"}).json()
        self.assertTrue(d["exists"])
        d = self.client.get(url, {"sku": "K24644.S16",
                                  "attrs": json.dumps([{"name": "color", "value": "white"},
                                                       {"name": "model", "value": "S16"}])}).json()
        self.assertFalse(d["exists"])
        self.assertNotIn("lookalike", d)

    def test_a_product_lists_its_groups_attributes_then_its_own(self, _up):
        from operating.views_warehouse import product_attribute_names
        for i, name in enumerate(["color", "model"]):
            CategoryVariantAttribute.objects.create(
                category=self.fabric, position=i,
                attribute=ProductVariantAttribute.objects.get_or_create(name=name)[0])
        self.assertEqual(product_attribute_names(category=self.fabric), ["color", "model"])
        self._receive([self._row("K24644.S11", ("yarn", "750 Mat"), ("color", "white"))])
        product = Product.objects.get(sku="K24644")
        self.assertEqual(product_attribute_names(product), ["color", "model", "yarn"])


class ProductGroupPresetTest(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser("group_tester", "g@t.t", "pw")
        self.client.force_login(user)
        self.group = ProductCategory.objects.create(name="ready-made_curtain")

    def test_the_group_page_saves_the_preset_in_order(self):
        url = reverse("marketing:product_group_detail", args=[self.group.pk])
        r = self.client.post(url, {"action": "save_settings", "name": self.group.name,
                                   "variant_attributes_sent": "1",
                                   "variant_attributes": ["Color", "Size Per Panel", "header", "color"]})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.group.variant_attribute_names(), ["color", "size per panel", "header"])
        page = self.client.get(url)
        self.assertContains(page, 'name="variant_attributes" value="size per panel"')

    def test_a_form_without_the_list_leaves_the_preset_alone(self):
        CategoryVariantAttribute.objects.create(
            category=self.group, attribute=ProductVariantAttribute.objects.create(name="color"))
        url = reverse("marketing:product_group_detail", args=[self.group.pk])
        self.client.post(url, {"action": "save_settings", "name": self.group.name})
        self.assertEqual(self.group.variant_attribute_names(), ["color"])

    def test_a_new_group_can_start_with_a_preset(self):
        r = self.client.post(reverse("marketing:product_group_create"),
                             {"name": "Towels", "variant_attributes_sent": "1",
                              "variant_attributes": ["color", "size"]})
        self.assertEqual(r.status_code, 200, r.content)
        group = ProductCategory.objects.get(pk=r.json()["id"])
        self.assertEqual(group.variant_attribute_names(), ["color", "size"])
