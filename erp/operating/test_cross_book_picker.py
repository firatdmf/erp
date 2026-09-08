"""What the order form is ALLOWED to show, and what it says about it.

The pickers stay inside the working book unless the form explicitly asks
past it (`cross_book=1`, the "show my other books" toggle). Widening the
view was never the danger — one order spanning two businesses was, and
the SAVE is what prevents that by splitting. See
test_cross_book_order_split for the other half.

Every row that can be picked names its book, because the line minted from
it carries that book to the save. A row that could not say which shelf it
came from would leave the save guessing.

Run with:
    python manage.py test operating.test_cross_book_picker
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from marketing.models import Product, ProductVariant

from .models import Warehouse, WarehouseProduct, WarehouseProductItem

SKU = "K24644.G07"


class CrossBookPicker(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")

        # The SAME variant standing on a shelf in each book — the case
        # that makes "which book?" a real question rather than a formality.
        product = Product.objects.create(title="Krep", sku="K24644")
        self.variant = ProductVariant.objects.create(
            product=product, variant_sku=SKU)
        self.l_item = self._stock(self.laleli, "L-0001")
        self.e_item = self._stock(self.ergene, "E-0001")

        User = get_user_model()
        user = User.objects.create_superuser("seller", "s@t.com", "pw")
        user.member.books.add(self.laleli, self.ergene)
        user.member.default_book = self.laleli
        user.member.save()
        self.client.force_login(user)

    def _stock(self, book, barcode):
        wh = Warehouse.objects.create(
            name=f"{book.name} depo", accounting_book=book)
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name="Krep", sku=SKU, quantity=Decimal("50"),
            catalog_variant=self.variant)
        return WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
            barcode=barcode, status="in_stock")

    def _rolls(self, **params):
        resp = self.client.get(
            reverse("operating:order_create_roll_list"), {"sku": SKU, **params})
        self.assertEqual(resp.status_code, 200)
        return json.loads(resp.content)["rolls"]

    # ── default: one book ───────────────────────────────────────────
    def test_the_roll_list_stays_in_the_working_book(self):
        barcodes = {r["barcode"] for r in self._rolls(book=self.laleli.pk)}
        self.assertEqual(barcodes, {"L-0001"})

    def test_the_toggle_opens_the_other_book(self):
        barcodes = {r["barcode"]
                    for r in self._rolls(book=self.laleli.pk, cross_book="1")}
        self.assertEqual(barcodes, {"L-0001", "E-0001"})

    def test_every_roll_row_names_its_book(self):
        """The card tags its line from this, and the save splits on the
        tag — a row that cannot say which shelf it came from would make
        the whole split guesswork."""
        for row in self._rolls(book=self.laleli.pk, cross_book="1"):
            self.assertIn("book_id", row)
            self.assertIn(row["book"], {"Laleli Fabric", "Ergene Fabric"})
        by_bc = {r["barcode"]: r for r in
                 self._rolls(book=self.laleli.pk, cross_book="1")}
        self.assertEqual(by_bc["L-0001"]["book_id"], self.laleli.pk)
        self.assertEqual(by_bc["E-0001"]["book_id"], self.ergene.pk)

    # ── the search ──────────────────────────────────────────────────
    def test_the_search_offers_one_row_per_book(self):
        """One variant on two books' shelves is not one sellable thing:
        the rows bill different accounts and ship off different shelves,
        so collapsing them would make the pick unable to say which."""
        resp = self.client.get(
            reverse("operating:product_autocomplete"),
            {"product": "Krep", "book": self.laleli.pk, "cross_book": "1"})
        body = resp.content.decode()
        self.assertIn("Laleli Fabric", body)
        self.assertIn("Ergene Fabric", body)
        # Both books' ids reach selectProduct, so the picked line knows
        # which shelf it came off.
        self.assertIn(f",{self.laleli.pk},'Laleli Fabric'", body)
        self.assertIn(f",{self.ergene.pk},'Ergene Fabric'", body)

    def test_the_search_stays_narrow_without_the_toggle(self):
        resp = self.client.get(
            reverse("operating:product_autocomplete"),
            {"product": "Krep", "book": self.laleli.pk})
        body = resp.content.decode()
        self.assertNotIn("Ergene Fabric", body)

    # ── the scan ────────────────────────────────────────────────────
    def test_a_scanned_barcode_reports_its_book(self):
        """A line minted straight from a scan has to be tagged like one
        picked out of the list, or scanning would dodge the split."""
        resp = self.client.get(
            reverse("operating:order_create_barcode_check"),
            {"barcode": "E-0001", "sku": SKU, "cross_book": "1"})
        d = json.loads(resp.content)
        self.assertTrue(d["ok"])
        self.assertEqual(d["book_id"], self.ergene.pk)
        self.assertEqual(d["book"], "Ergene Fabric")

    def test_a_scan_cannot_reach_another_book_without_the_toggle(self):
        resp = self.client.get(
            reverse("operating:order_create_barcode_check"),
            {"barcode": "E-0001", "sku": SKU, "book": self.laleli.pk})
        self.assertEqual(resp.status_code, 404)
