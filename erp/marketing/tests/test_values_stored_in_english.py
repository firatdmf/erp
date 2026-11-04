"""A value is stored in English, whatever language it was typed in.

The catalog keeps one spelling of each value, its English key ("cream"),
and reads it in other languages through the catalog wordings ("Krem").
A Turkish word used to be turned into English by a list of 28 colours
written into the code; now the wordings say what a word is, for every
attribute and every language, and a word nobody has worded asks for its
English — with Gemini's guess to check — and is remembered as that
value's wording.

Run with:
    python manage.py test marketing.tests.test_values_stored_in_english
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from marketing.attributes import english_value, fold_term, value_suggestions
from marketing.models import CatalogWording


def _word(key, text, scope="color", language="tr"):
    CatalogWording.objects.create(kind="value", scope=scope, key=key, language=language, text=text)


class EnglishValueTest(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        _word("cream", "Krem")
        _word("silver", "Gümüş")
        _word("red", "Kırmızı")
        _word("cream", "Кремовый", language="ru")
        _word("light", "Açık", scope="")

    def test_folding_ignores_case_accents_and_dotless_i(self):
        self.assertEqual(fold_term("GÜMÜŞ"), fold_term("gumus"))
        self.assertEqual(fold_term("KIRMIZI"), fold_term("Kırmızı"))
        self.assertEqual(fold_term("İPEK"), "ipek")

    def test_a_worded_word_is_its_english_key(self):
        self.assertEqual(english_value("color", "KREM"), "cream")
        self.assertEqual(english_value("color", "gumus"), "silver")
        self.assertEqual(english_value("color", "КРЕМОВЫЙ"), "cream")
        self.assertEqual(english_value("color", "cream"), "cream")

    def test_spaces_do_not_count(self):
        _word("ivory", "Fildişi")
        self.assertEqual(english_value("color", "Fil Dişi"), "ivory")
        self.assertEqual(value_suggestions("color", "fil d", language="tr")[0]["value"], "ivory")

    def test_a_wording_holds_under_its_own_attribute_only(self):
        self.assertIsNone(english_value("header", "krem"))

    def test_a_phrase_and_a_combination_are_read_in_parts(self):
        self.assertEqual(english_value("color", "açık krem"), "light cream")
        self.assertEqual(english_value("color", "krem+gümüş"), "cream+silver")
        self.assertEqual(english_value("color", "krem+V-356"), "cream+V-356")

    def test_a_word_nobody_worded_is_unknown(self):
        self.assertIsNone(english_value("color", "fildişi"))
        self.assertIsNone(english_value("color", "açık fildişi"))

    def test_part_of_a_word_offers_the_values_it_could_be(self):
        found = value_suggestions("color", "kre", language="tr")
        self.assertEqual(found[0], {"value": "cream", "label": "Krem"})
        self.assertEqual(value_suggestions("color", "ivo", stored=["ivory"], language="en"),
                         [{"value": "ivory", "label": "Ivory"}])


class EndpointsTest(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        _word("cream", "Krem")
        self.client.force_login(get_user_model().objects.create_superuser("w", "w@w.w", "pw"))

    def test_suggest_names_the_whole_word_and_the_choices(self):
        d = self.client.get(reverse("marketing:attribute_value_suggest"),
                            {"attribute": "color", "q": "KREM"}).json()
        self.assertEqual(d["exact"], "cream")
        self.assertEqual(d["results"][0]["value"], "cream")
        d = self.client.get(reverse("marketing:attribute_value_suggest"),
                            {"attribute": "color", "q": "fildişi"}).json()
        self.assertIsNone(d["exact"])

    def test_a_confirmed_new_value_keeps_the_typed_word_as_its_wording(self):
        url = reverse("marketing:attribute_value_word")
        r = self.client.post(url, {"attribute": "color", "value": "ivory",
                                   "language": "tr", "text": "Fildişi"})
        self.assertTrue(r.json()["saved"])
        self.assertEqual(english_value("color", "FİLDİŞİ"), "ivory")
        # A wording already written is left alone; English needs none.
        self.assertFalse(self.client.post(url, {"attribute": "color", "value": "ivory",
                                                "language": "tr", "text": "Kemik"}).json()["saved"])
        self.assertFalse(self.client.post(url, {"attribute": "color", "value": "ivory",
                                                "language": "en", "text": "Ivory"}).json()["saved"])
        self.assertEqual(CatalogWording.objects.get(key="ivory").text, "Fildişi")

    def test_gemini_only_suggests(self):
        url = reverse("marketing:attribute_value_translate")
        with patch("marketing.wording_suggest._ask", return_value={"en": "ivory"}) as ask:
            d = self.client.post(url, {"attribute": "color", "text": "fildişi",
                                       "source": "tr", "targets": "en"}).json()
        self.assertEqual((d["suggested"], d["language"]), ({"en": "ivory"}, "tr"))
        # The catalog's own wordings go with the question.
        self.assertIn("cream = Krem", ask.call_args[0][0])
        self.assertFalse(CatalogWording.objects.filter(key="ivory").exists())

    def test_the_language_of_a_word_is_worked_out(self):
        # Typed on an English screen, "Fil Dişi" is still Turkish.
        with patch("marketing.wording_suggest._ask",
                   return_value={"en": "ivory", "language": "tr"}) as ask:
            d = self.client.post(reverse("marketing:attribute_value_translate"),
                                 {"attribute": "color", "text": "Fil Dişi",
                                  "source": "auto", "targets": "en"}).json()
        self.assertEqual((d["suggested"], d["language"]), ({"en": "ivory"}, "tr"))
        self.assertIn('"language"', ask.call_args[0][0])

    def test_gemini_is_asked_over_its_rest_api(self):
        from marketing.wording_suggest import suggest_wordings

        class Answer:
            def raise_for_status(self):
                pass

            def json(self):
                return {"candidates": [{"content": {"parts": [{"text": '{"en": "ivory", "language": "tr"}'}]}}]}

        with patch("marketing.wording_suggest._env",
                   side_effect=lambda k: "key" if k == "GOOGLE_AI_API_KEY" else None), \
                patch("requests.post", return_value=Answer()) as post:
            self.assertEqual(suggest_wordings("color", "fildişi", "auto", ["en"]),
                             ({"en": "ivory"}, "tr"))
        self.assertIn("gemini-2.5-flash:generateContent", post.call_args[0][0])
        self.assertEqual(post.call_args[1]["headers"], {"x-goog-api-key": "key"})

    def test_no_key_means_no_suggestion(self):
        with patch("marketing.wording_suggest._env", return_value=None):
            d = self.client.post(reverse("marketing:attribute_value_translate"),
                                 {"attribute": "color", "text": "fildişi",
                                  "source": "tr", "targets": "en"}).json()
        self.assertEqual(d["suggested"], {})

    def test_the_wording_page_offers_suggestions_and_a_missing_filter(self):
        r = self.client.get(reverse("marketing:catalog_wording"), {"section": "color"})
        self.assertContains(r, 'class="at-suggest"')
        self.assertContains(r, 'id="atMissing"')


class GoodsReceiptOffersValuesTest(TestCase):
    def test_the_value_fields_search_the_wordings(self):
        from django.test import Client
        from accounting.models import Book
        from operating.models import Warehouse
        book = Book.objects.create(name="Laleli Fabric")
        Warehouse.objects.create(name="Fabrika", accounting_book=book)
        client = Client()
        client.force_login(get_user_model().objects.create_superuser("g", "g@g.g", "pw"))
        r = client.get(reverse("accounts:goods_receipt", kwargs={"book_id": book.pk}))
        self.assertContains(r, reverse("marketing:attribute_value_suggest"))
        self.assertContains(r, "npValueAskEnglish")
