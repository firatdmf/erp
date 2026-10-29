"""A scan may only reach the shelves the member is assigned.

The barcode endpoints answer from every book the member may work in —
the save splits a basket that spans two into one order per book, so a
line from any of them is saveable. A book the member is NOT assigned is
another business's stock they have no say over, and stays out of reach.

The form still sends the book it is working in, which decides whose
stock a printed barcode (goods sold by count) comes off first.

Run with:
    python manage.py test operating.test_cross_book_scan_scope
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from marketing.models import Product, ProductVariant

from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem

L_SKU = "K24644.G07"
E_SKU = "K24777.B02"
A_SKU = "K24888.C03"


class ScanStaysInScope(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.almaty = Book.objects.create(name="Almaty")
        self._stock(self.laleli, L_SKU, "Krep", "L-0001")
        self._stock(self.ergene, E_SKU, "Tul", "E-0001")
        self._stock(self.almaty, A_SKU, "Saten", "A-0001")

        # Not a superuser: a superuser is assigned every book implicitly,
        # which would hide the one boundary this file is about.
        User = get_user_model()
        user = User.objects.create_user("seller", "s@t.com", "pw")
        user.member.books.set([self.laleli, self.ergene])
        user.member.default_book = self.laleli
        user.member.save()
        self.client.force_login(user)

    def _stock(self, book, sku, title, barcode):
        p = Product.objects.create(title=title, sku=sku.split(".")[0])
        v = ProductVariant.objects.create(product=p, variant_sku=sku)
        wh = Warehouse.objects.create(name=f"{book.name} depo", accounting_book=book)
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name=title, sku=sku, quantity=Decimal("50"),
            catalog_variant=v)
        WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
            barcode=barcode, status="in_stock")

    def _resolve(self, barcode, **params):
        return self.client.get(
            reverse("operating:order_create_barcode_resolve"),
            {"barcode": barcode, **params})

    def _check(self, barcode, sku, **params):
        return self.client.get(
            reverse("operating:order_create_barcode_check"),
            {"barcode": barcode, "sku": sku, **params})

    def test_the_working_book_scans(self):
        resp = self._resolve("L-0001", book=self.laleli.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["roll"]["book_id"], self.laleli.pk)

    def test_another_assigned_book_scans_and_says_whose_it_is(self):
        """The save splits, so the line this mints is saveable — and the
        book travels with it so the save knows where it goes."""
        for resp in (self._resolve("E-0001", book=self.laleli.pk),
                     self._check("E-0001", E_SKU, book=self.laleli.pk)):
            self.assertEqual(resp.status_code, 200, resp.content)
            d = json.loads(resp.content)
            book_id = d["roll"]["book_id"] if "roll" in d else d["book_id"]
            self.assertEqual(book_id, self.ergene.pk)

    def test_an_unassigned_book_stays_out_of_reach(self):
        for resp in (self._resolve("A-0001", book=self.laleli.pk),
                     self._check("A-0001", A_SKU, book=self.laleli.pk)):
            self.assertEqual(resp.status_code, 404)
            self.assertNotIn("Almaty", resp.content.decode())

    def test_naming_an_unassigned_book_does_not_widen_the_scan(self):
        """`book` arrives from the browser; it only orders the answer."""
        resp = self._resolve("A-0001", book=self.almaty.pk)
        self.assertEqual(resp.status_code, 404)

    def test_a_genuinely_unknown_barcode_still_says_not_found(self):
        resp = self._resolve("NO-SUCH-CODE", book=self.laleli.pk)
        self.assertEqual(resp.status_code, 404)

    # ── the form sends its working book ─────────────────────────────
    def test_every_picker_fetch_carries_its_scope(self):
        """Guards the client half: the working book decides whose stock
        comes first, so a call site that forgets it would take another
        book's stock ahead of the form's own."""
        with open("operating/templates/operating/partials/"
                  "create_order_form.html", encoding="utf-8") as fh:
            form = fh.read()
        import re
        # Each picker URL, plus the statement that follows it — the
        # window is generous because these calls wrap across lines.
        marks = [m for m in re.finditer(
            r"order_create_barcode_resolve|order_create_barcode_check|ROLL_LIST_URL",
            form)]
        windows = [form[m.start():m.start() + 320] for m in marks]
        fetches = [w for w in windows if "encodeURIComponent" in w]
        self.assertTrue(fetches, "no picker fetches found — did the URLs move?")
        for w in fetches:
            self.assertIn("coScopeParams", w,
                          "unscoped picker call: " + w.split("\n")[0][:100])
