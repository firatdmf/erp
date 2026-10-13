"""A catalog term is stored once and worded per language.

The key is English ("dark_cream"). Its Turkish, Russian and Polish used to
be a table in the storefront's code, so the ERP printed the key to
everybody and a new value waited for a storefront release. The wordings
are kept in the ERP now: written on one page, read by the ERP for whoever
is looking, and handed to the storefront by one endpoint. A term is an
attribute's name, one of its values, or a product group's name; the
attributes on a variant and the ones on a product share them.

Run with:
    python manage.py test marketing.tests.test_attribute_wording
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from marketing.attributes import attribute_label, display_value, group_label, wording
from marketing.models import (CatalogWording, Product, ProductAttribute, ProductCategory,
                              ProductVariant, ProductVariantAttribute,
                              ProductVariantAttributeValue)


def word(kind, scope, key, language, text):
    return CatalogWording.objects.create(
        kind=kind, scope=scope, key=key, language=language, text=text)


class WordingTest(TestCase):
    def setUp(self):
        cache.clear()
        word("value", "yarn", "750_matte_pearl", "tr", "750 MAT SEDEF")
        word("value", "yarn", "750_matte_pearl", "en", "750 Matte Pearl")
        word("name", "", "color", "tr", "Renk")

    def test_a_value_reads_in_the_readers_language(self):
        with translation.override("tr"):
            self.assertEqual(display_value("yarn", "750_matte_pearl"), "750 MAT SEDEF")
        with translation.override("en"):
            self.assertEqual(display_value("yarn", "750_matte_pearl"), "750 Matte Pearl")

    def test_a_value_nobody_worded_reads_from_its_key(self):
        with translation.override("tr"):
            self.assertEqual(display_value("color", "dark_cream"), "Dark cream")
            self.assertEqual(display_value("width", "250"), "250 cm")

    def test_an_attributes_name_is_worded_too(self):
        with translation.override("tr"):
            self.assertEqual(attribute_label("color"), "Renk")
            self.assertEqual(attribute_label("yarn"), "Yarn")
        with translation.override("en"):
            self.assertEqual(attribute_label("color"), "Color")

    def test_spelling_differences_are_one_term(self):
        word("name", "", "Sheet Type", "tr", "Çarşaf Tipi")
        self.assertEqual(CatalogWording.objects.get(text="Çarşaf Tipi").key, "sheet type")
        self.assertEqual(wording("sheet_type", "", "tr"), "Çarşaf Tipi")
        self.assertEqual(wording("Sheet  Type", "", "tr"), "Çarşaf Tipi")

    def test_a_value_worded_for_any_attribute_yields_to_its_own(self):
        word("value", "", "yes", "tr", "Evet")
        word("value", "warranty", "yes", "tr", "Var")
        self.assertEqual(wording("fast_shipping", "yes", "tr"), "Evet")
        self.assertEqual(wording("warranty", "Yes", "tr"), "Var")

    def test_a_product_group_is_worded(self):
        word("group", "", "ready-made_curtain", "tr", "Hazır Perde")
        self.assertEqual(group_label("ready-made_curtain", "tr"), "Hazır Perde")
        self.assertEqual(group_label("fabric", "tr"), "fabric")

    def test_a_new_wording_is_read_at_once(self):
        with translation.override("ru"):
            self.assertEqual(display_value("color", "white"), "White")
            word("value", "color", "White", "ru", "Белый")
            self.assertEqual(display_value("color", "white"), "Белый")

    def test_one_wording_per_term_and_language(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            word("value", "yarn", "750 matte pearl", "tr", "again")


class WordingPageTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client.force_login(
            get_user_model().objects.create_superuser("boss", "boss@example.com", "pw"))
        color = ProductVariantAttribute.objects.create(name="color")
        white = ProductVariantAttributeValue.objects.create(
            product_variant_attribute=color, product_variant_attribute_value="white")
        group = ProductCategory.objects.create(name="ready-made_curtain")
        product = Product.objects.create(title="Sable", sku="sable", category=group)
        variant = ProductVariant.objects.create(product=product, variant_sku="sable-white")
        variant.product_variant_attribute_values.add(white)
        ProductAttribute.objects.create(product=product, name="Sheet Type", value="Fitted")
        ProductAttribute.objects.create(product=product, name="Color", value="white")
        self.url = reverse("marketing:attribute_translations")

    def _keys(self, section):
        response = self.client.get(self.url, {"section": section})
        self.assertEqual(response.status_code, 200)
        return [(r["key"], r["carried"]) for r in response.context["rows"]]

    def test_names_come_from_variants_and_products_alike(self):
        self.assertEqual(self._keys("names"), [("color", None), ("sheet type", None)])

    def test_an_attributes_values_are_counted_across_both(self):
        self.assertEqual(self._keys("color"), [("white", 2)])
        self.assertEqual(self._keys("sheet type"), [("fitted", 1)])

    def test_groups_are_listed_with_their_products(self):
        self.assertEqual(self._keys("groups"), [("ready-made curtain", 1)])

    def _post(self, section, **fields):
        data = {"section": section, "rows": "1", "key_0": "white"}
        data.update(fields)
        return self.client.post(self.url, data)

    def test_saving_writes_changes_and_clears_what_was_emptied(self):
        self._post("color", text_0_tr="Beyaz", text_0_ru="Белый")
        self.assertEqual(
            sorted(CatalogWording.objects.values_list("kind", "scope", "key", "language", "text")),
            [("value", "color", "white", "ru", "Белый"), ("value", "color", "white", "tr", "Beyaz")])
        self._post("color", text_0_tr="Bembeyaz")
        self.assertEqual(
            sorted(CatalogWording.objects.values_list("key", "language", "text")),
            [("white", "tr", "Bembeyaz")])

    def test_a_term_nothing_carries_yet_can_be_added(self):
        self._post("color", new_key="Dark_Cream", new_text_tr="Koyu krem")
        self.assertEqual(wording("color", "dark_cream", "tr"), "Koyu krem")
        self.assertIn(("dark cream", 0), self._keys("color"))

    def test_the_storefront_is_handed_every_wording(self):
        self._post("color", text_0_tr="Beyaz", text_0_pl="Biały")
        self.client.post(self.url, {"section": "names", "rows": "1", "key_0": "color",
                                    "text_0_tr": "Renk"})
        self.client.post(self.url, {"section": "any", "rows": "0", "new_key": "yes",
                                    "new_text_tr": "Evet"})
        self.client.post(self.url, {"section": "groups", "rows": "1",
                                    "key_0": "ready-made curtain", "text_0_tr": "Hazır Perde"})
        self.client.logout()
        answer = self.client.get(reverse("marketing:attribute_translations_api")).json()
        self.assertEqual(answer, {
            "names": {"color": {"tr": "Renk"}},
            "values": {"color": {"white": {"tr": "Beyaz", "pl": "Biały"}},
                       "": {"yes": {"tr": "Evet"}}},
            "groups": {"ready-made curtain": {"tr": "Hazır Perde"}},
        })

    def test_the_variant_list_prints_the_wording(self):
        self._post("color", text_0_tr="Beyaz")
        self.client.post(self.url, {"section": "names", "rows": "1", "key_0": "color",
                                    "text_0_tr": "Renk"})
        with translation.override("tr"):
            from marketing.templatetags.attribute_wording import worded_name, worded_value
            row = ProductVariantAttributeValue.objects.get()
            self.assertEqual((worded_name(row), worded_value(row)), ("Renk", "Beyaz"))
