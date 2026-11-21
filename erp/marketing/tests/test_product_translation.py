"""A product's Turkish and Russian text, written by Gemini from its English.

Run with:
    python manage.py test marketing.tests.test_product_translation
"""
import json
from unittest.mock import patch

from django.test import TestCase

from marketing import product_translation as pt
from marketing.gemini import GeminiUnavailable
from marketing.models import Product


def stored(product):
    product.refresh_from_db()
    return pt.parse(product.description)


def answer_for(prompt):
    """Gemini as the tests need it: every product, every key, marked by language."""
    items = json.loads(prompt.split("Products, as JSON:\n", 1)[1].split("\nAnswer with", 1)[0])["items"]
    return json.dumps({"items": [
        {"id": item["id"], **{lang: {k: f"{lang}:{v}" for k, v in item.items() if k != "id"}
                              for lang in pt.TARGETS}}
        for item in items]})


def fake_gemini(parts, **kwargs):
    return answer_for(parts[0])


class WithEnglish(TestCase):
    def test_the_posted_english_replaces_the_stored_and_the_rest_stays(self):
        old = json.dumps({"translations": {"en": {"title": "Old name", "description": "<p>Old</p>"},
                                           "tr": {"description": "<p>Eski</p>"}},
                          "translated_from": {"tr": "abc"}})
        posted = json.dumps({"translations": {"en": {"description": "<p>New</p>"}}})
        data = pt.parse(pt.with_english(old, posted))
        # The name is the product's title: the English keeps none of its own.
        self.assertEqual(data["translations"]["en"], {"description": "<p>New</p>"})
        self.assertEqual(data["translations"]["tr"], {"description": "<p>Eski</p>"})
        self.assertEqual(data["translated_from"], {"tr": "abc"})

    def test_nothing_left_is_stored_as_nothing(self):
        self.assertIsNone(pt.with_english(None, ""))

    def test_the_form_keeps_the_texts_when_the_page_sends_none(self):
        from marketing.forms import ProductForm

        product = Product.objects.create(
            title="Sheet", sku="SHEET1",
            description=json.dumps({"translations": {"tr": {"description": "<p>Çarşaf</p>"}}}))
        form = ProductForm({"title": "Sheet"}, instance=product, is_update=True)
        form.cleaned_data = {"description": ""}
        self.assertEqual(form.clean_description(), product.description)


@patch("marketing.gemini.ask_gemini", side_effect=fake_gemini)
class Translate(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            title="Florenza", sku="K12767",
            description=json.dumps({"translations": {"en": {"description": "<p>Sheer</p>"}}}))

    def test_the_english_is_written_in_every_storefront_language(self, gemini):
        counts = pt.translate(pause=0)
        data = stored(self.product)
        self.assertEqual(data["translations"]["tr"], {"title": "tr:Florenza", "description": "tr:<p>Sheer</p>"})
        self.assertEqual(data["translations"]["ru"], {"title": "ru:Florenza", "description": "ru:<p>Sheer</p>"})
        self.assertEqual(data["translations"]["en"], {"description": "<p>Sheer</p>"})
        self.assertEqual(counts["translated"], 1)

    def test_unchanged_english_is_not_asked_again(self, gemini):
        pt.translate(pause=0)
        gemini.reset_mock()
        self.assertEqual(pt.translate(pause=0)["translated"], 0)
        gemini.assert_not_called()

    def test_a_changed_name_is_translated_again(self, gemini):
        pt.translate(pause=0)
        Product.objects.filter(pk=self.product.pk).update(title="Florenza Sheer")
        pt.translate(pause=0)
        self.assertEqual(stored(self.product)["translations"]["tr"]["title"], "tr:Florenza Sheer")

    def test_a_translation_typed_by_hand_stays_until_its_english_changes(self, gemini):
        Product.objects.filter(pk=self.product.pk).update(description=json.dumps({"translations": {
            "en": {"description": "<p>Sheer</p>"}, "tr": {"description": "<p>Tül</p>"}}}))
        pt.translate(pause=0)
        data = stored(self.product)
        self.assertEqual(data["translations"]["tr"], {"description": "<p>Tül</p>"})
        self.assertEqual(data["translations"]["ru"]["description"], "ru:<p>Sheer</p>")
        self.assertEqual(set(data["translated_from"]), {"tr", "ru"})

        Product.objects.filter(pk=self.product.pk).update(title="Florenza Sheer")
        pt.translate(pause=0)
        self.assertEqual(stored(self.product)["translations"]["tr"]["description"], "tr:<p>Sheer</p>")

    def test_english_changed_while_gemini_worked_is_left_for_the_next_run(self, gemini):
        def change_then_answer(parts, **kwargs):
            Product.objects.filter(pk=self.product.pk).update(title="Renamed")
            return answer_for(parts[0])

        gemini.side_effect = change_then_answer
        pt.translate(pause=0)
        self.assertNotIn("tr", stored(self.product).get("translations", {}))

    def test_a_product_missing_from_the_answer_is_asked_again_on_its_own(self, gemini):
        other = Product.objects.create(title="Silk", sku="SLK")
        calls = []

        def drop_the_last(parts, **kwargs):
            answer = json.loads(answer_for(parts[0]))
            calls.append(len(answer["items"]))
            if len(answer["items"]) > 1:
                answer["items"] = answer["items"][:-1]
            return json.dumps(answer)

        gemini.side_effect = drop_the_last
        counts = pt.translate(pause=0)
        self.assertEqual(calls, [2, 1])
        self.assertEqual(counts["translated"], 2)
        self.assertEqual(stored(other)["translations"]["ru"]["title"], "ru:Silk")

    def test_a_translation_carrying_another_products_name_is_asked_again_alone(self, gemini):
        Product.objects.filter(pk=self.product.pk).update(title="EVAN sheet set")
        other = Product.objects.create(title="LOVE sheet set", sku="LOVE")
        sizes = []

        def cross_the_first(parts, **kwargs):
            answer = json.loads(answer_for(parts[0]))
            sizes.append(len(answer["items"]))
            if len(answer["items"]) > 1:
                answer["items"][0]["ru"]["title"] = "LOVE | Комплект"
            return json.dumps(answer)

        gemini.side_effect = cross_the_first
        pt.translate(pause=0)
        self.assertEqual(sizes, [2, 1])
        self.assertEqual(stored(self.product)["translations"]["ru"]["title"], "ru:EVAN sheet set")
        self.assertEqual(stored(other)["translations"]["ru"]["title"], "ru:LOVE sheet set")

    def test_a_code_the_english_lacks_is_refused(self, gemini):
        self.assertTrue(pt._foreign_words(pt._words("Florenza"), {"title": "Florenza K25318"}, "tr"))
        self.assertFalse(pt._foreign_words(pt._words("Florenza sheer"), {"title": "Florenza Şeffaf"}, "tr"))
        self.assertFalse(pt._foreign_words(pt._words("Florenza sheer"), {"title": "Florenza тюль"}, "ru"))

    def test_gemini_out_leaves_the_text_as_it_is(self, gemini):
        gemini.side_effect = GeminiUnavailable("no key")
        counts = pt.translate(pause=0)
        self.assertEqual(counts, {"translated": 0, "kept": 0, "left": 1})
        self.assertNotIn("translated_from", stored(self.product))

    def test_the_glossary_carries_the_catalogs_own_words(self, gemini):
        from django.core.cache import cache

        from marketing.models import CatalogWording

        CatalogWording.objects.create(kind="value", scope="", key="matte nacre",
                                      language="tr", text="Mat Sedef")
        cache.clear()
        Product.objects.filter(pk=self.product.pk).update(title="Matte nacre sheer")
        pt.translate(pause=0)
        self.assertIn("matte nacre = Mat Sedef (Turkish)", gemini.call_args.args[0][0])
