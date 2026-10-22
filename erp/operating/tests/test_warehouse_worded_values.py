"""A warehouse row says what its variant is in the reader's language.

A row's name is typed once, in one language ("2086 ALTIN EKRU"), and a sales
rep who reads Turkish or Russian but not English cannot read the catalog's
English values ("gold+ecru"). Under the name the row prints its variant's
values through the catalog's wordings, so the same row reads "Altın + Ekru ·
320 cm" to her and "Gold + Ecru · 320 cm" in English.

Run with:
    python manage.py test operating.tests.test_warehouse_worded_values
"""
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from marketing.attributes import WORDING_VALUE, forget_wordings, term_key
from marketing.models import CatalogWording
from operating.catalog_sync import sync_roll_to_catalog
from operating.models import Warehouse, WarehouseProduct


def _worded(html):
    return [re.sub(r"\s+", " ", m).strip()
            for m in re.findall(r'<div class="psub wh-worded">(.*?)</div>', html, re.S)]


class WarehouseRowsAreWordedTest(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric", base_currency=usd)
        self.wh = Warehouse.objects.create(name="Laleli", accounting_book=self.book)
        for language, text in (("tr", "Altın + Ekru"), ("en", "Gold + Ecru")):
            CatalogWording.objects.create(kind=WORDING_VALUE, scope="color",
                                          key=term_key("gold+ecru"), language=language, text=text)
        forget_wordings()
        self._row("2086.GOLD_ECRU-320", "2086 ALTIN EKRU", [("color", "gold+ecru"), ("width", "320")])

        user = get_user_model().objects.create_user("rep", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _row(self, sku, name, attributes):
        _p, variant, _pc, _vc = sync_roll_to_catalog(
            base_name="2086", variant_sku=sku, attributes=attributes)
        return WarehouseProduct.objects.create(
            warehouse=self.wh, name=name, sku=sku, quantity=Decimal("10"), catalog_variant=variant)

    def _list(self, language, **params):
        self.client.cookies["django_language"] = language
        resp = self.client.get(reverse("operating:warehouse_detail", args=[self.wh.pk]), params)
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_a_turkish_reader_reads_the_colour_in_turkish(self):
        self.assertIn("Altın + Ekru · 320 cm", _worded(self._list("tr")))

    def test_an_english_reader_reads_it_in_english(self):
        self.assertIn("Gold + Ecru · 320 cm", _worded(self._list("en")))

    def test_the_typed_name_is_still_there(self):
        self.assertIn("2086 ALTIN EKRU", self._list("tr"))

    def test_a_value_nobody_worded_reads_as_stored(self):
        self._row("2086.V101-320", "2086 V-101", [("color", "v-101"), ("width", "320")])
        self.assertIn("V-101 · 320 cm", _worded(self._list("tr")))

    def test_an_opened_group_is_worded_too(self):
        self.client.cookies["django_language"] = "tr"
        resp = self.client.get(reverse("operating:warehouse_group_variants", args=[self.wh.pk]),
                               {"base": "2086"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Altın + Ekru · 320 cm", _worded(resp.content.decode()))

    def test_more_rows_do_not_mean_more_queries(self):
        self._list("tr")  # warm the wordings cache
        with CaptureQueriesContext(connection) as few:
            self._list("tr")
        for i in range(6):
            self._row(f"2086.C{i}-320", f"2086 C{i}", [("color", f"c{i}"), ("width", "320")])
        with CaptureQueriesContext(connection) as many:
            self._list("tr")
        self.assertEqual(len(many), len(few))
