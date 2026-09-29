"""The printed quote is cut the way acceptance cuts it: book by book, each
book's lines the order that book will get, and within a book by the
warehouse whose shelf the rolls are picked from.

Run with:
    python manage.py test marketing.tests.test_quote_print_sections
"""
import json
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from crm.models import Contact
from marketing.models import Product, ProductVariant, Quote
from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


class PrintedQuoteSectionsTest(TestCase):
    def setUp(self):
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.customer = Contact.objects.create(name="Hanefi")
        product = Product.objects.create(title="Velvet 320", sku="V320", price=10)
        self.variant = ProductVariant.objects.create(product=product, variant_sku="V320.ECRU")
        admin = get_user_model().objects.create_superuser(
            username="firat_qp", password="pw", email="a@b.c")
        self.client.force_login(admin)

    def _roll(self, barcode, metres, book, warehouse):
        wh, _ = Warehouse.objects.get_or_create(name=warehouse, accounting_book=book)
        wp, _ = WarehouseProduct.objects.get_or_create(
            warehouse=wh, catalog_variant=self.variant,
            defaults={"name": "Velvet", "sku": self.variant.variant_sku})
        return WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal(metres), quantity_remaining=Decimal(metres),
            barcode=barcode, status="in_stock")

    def _quote(self, *lines):
        body = {
            "book_id": self.ergene.pk,
            "customer": {"type": "contact", "pk": self.customer.pk},
            "currency": "", "date": "2026-09-29", "valid_until": "", "notes": "",
            "items": [{"sku": "V320.ECRU", "quantity": "", "unit": "mt", "price": price,
                       "rolls": [{"id": r.pk, "quantity": ""} for r in rolls]}
                      for price, rolls in lines],
        }
        r = self.client.post(reverse("marketing:quote_create"), data=json.dumps(body),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        return Quote.objects.get(pk=r.json()["quote_id"])

    def _print(self, quote):
        page = self.client.get(reverse("marketing:quote_print", args=[quote.pk]) + "?html=1")
        self.assertEqual(page.status_code, 200)
        body = page.content.decode()
        body = body[body.index("<tbody>"):body.index("</tbody>")]
        return [(cls, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner)).strip())
                for cls, inner in re.findall(r'<tr(?: class="([^"]*)")?>(.*?)</tr>', body, re.S)]

    def test_books_then_warehouses_each_with_their_own_lines(self):
        quote = self._quote(
            ("2", [self._roll("E-1", "20", self.ergene, "Ergene Fabrika")]),
            ("3", [self._roll("L-1", "10", self.laleli, "Laleli Fabrika"),
                   self._roll("L-2", "5", self.laleli, "Laleli")]),
        )
        rows = self._print(quote)
        heads = [(cls, text) for cls, text in rows if cls]
        # The quote's own book first, then the other; each warehouse under
        # its book, alphabetically; no subtotals — one total at the foot.
        self.assertEqual([cls for cls, _ in heads],
                         ["grp", "wh", "grp", "wh", "wh", "grand"])
        self.assertIn("Ergene Fabric", heads[0][1])
        self.assertIn("Ergene Fabrika", heads[1][1])
        self.assertIn("Laleli Fabric", heads[2][1])
        self.assertTrue(heads[3][1].startswith("Laleli ·"), heads[3][1])
        self.assertIn("Laleli Fabrika", heads[4][1])
        self.assertIn("$85.00", heads[5][1])

        # The Laleli line prints under each warehouse with that shelf's
        # rolls and metres, not the whole line twice.
        lines = [text for cls, text in rows if not cls]
        self.assertEqual(len(lines), 3)
        self.assertIn("5 mt 1 roll", lines[1]); self.assertIn("$15.00", lines[1])
        self.assertIn("10 mt 1 roll", lines[2]); self.assertIn("$30.00", lines[2])

    def test_the_customers_copy_counts_rolls_but_names_none(self):
        """Barcodes are for picking — the packing list's, not the quote's."""
        quote = self._quote(("2", [self._roll("E-1", "20", self.ergene, "Ergene Fabrika"),
                                   self._roll("E-2", "21", self.ergene, "Ergene Fabrika")]))
        page = self.client.get(reverse("marketing:quote_print", args=[quote.pk]) + "?html=1")
        self.assertContains(page, "2 rolls")
        self.assertNotContains(page, "E-1")
        self.assertNotContains(page, "E-2")

    def test_one_book_and_no_rolls_prints_plainly(self):
        body = {
            "book_id": self.ergene.pk,
            "customer": {"type": "contact", "pk": self.customer.pk},
            "currency": "", "date": "2026-09-29", "valid_until": "", "notes": "",
            "items": [{"sku": "", "description": "Cutting service", "quantity": "1",
                       "unit": "", "price": "15"}],
        }
        r = self.client.post(reverse("marketing:quote_create"), data=json.dumps(body),
                             content_type="application/json")
        rows = self._print(Quote.objects.get(pk=r.json()["quote_id"]))
        self.assertEqual([cls for cls, _ in rows], ["", "grand"])
