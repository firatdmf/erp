"""A scan may only reach the shelves the order can actually be saved with.

The search and the roll list were scoped to the working book; the two
BARCODE endpoints were not, because the form never sent them a book. So
the global scanner on a Laleli order resolved an Ergene roll and minted a
line tagged Ergene — a line that order can never be saved with, because
an order belongs to one book. The refusal came at save time
("That line belongs to a different book"), long after the mistake, and
with the roll already on the card.

Scope now travels with every picker request: a card pins its own book,
everything else takes the form's working book, widened only by the
"other books" toggle. A barcode that really is on another of the
member's shelves says so by name instead of "no such barcode".

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

from .models import Warehouse, WarehouseProduct, WarehouseProductItem

L_SKU = "K24644.G07"
E_SKU = "K24777.B02"


class ScanStaysInScope(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.l_sku = self._stock(self.laleli, L_SKU, "Krep", "L-0001")
        self.e_sku = self._stock(self.ergene, E_SKU, "Tul", "E-0001")

        User = get_user_model()
        user = User.objects.create_superuser("seller", "s@t.com", "pw")
        user.member.books.add(self.laleli, self.ergene)
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
        return sku

    def _resolve(self, barcode, **params):
        return self.client.get(
            reverse("operating:order_create_barcode_resolve"),
            {"barcode": barcode, **params})

    def _check(self, barcode, sku, **params):
        return self.client.get(
            reverse("operating:order_create_barcode_check"),
            {"barcode": barcode, "sku": sku, **params})

    # ── the bug ─────────────────────────────────────────────────────
    def test_an_unscoped_scan_reaches_every_book_the_member_has(self):
        """The hazard itself, pinned so it cannot be forgotten.

        Asked with no book, these endpoints answer from every shelf the
        member may see — right for callers that mean it, and exactly what
        the order form used to do by omission. Nothing here is a fault in
        the endpoint: it is why the FORM must always say which book, and
        why test_every_picker_fetch_carries_its_scope is the guard that
        actually fails when this regresses.
        """
        resp = self._resolve("E-0001")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content)["roll"]["book_id"], self.ergene.pk)

    def test_the_global_scanner_cannot_reach_another_book(self):
        """Given the book the form now sends, an Ergene barcode scanned
        onto a Laleli order is refused — where it used to resolve and
        mint a line that order could never be saved with."""
        resp = self._resolve("E-0001", book=self.laleli.pk)
        self.assertEqual(resp.status_code, 404)

    def test_a_card_scan_cannot_reach_another_book(self):
        resp = self._check("E-0001", E_SKU, book=self.laleli.pk)
        self.assertEqual(resp.status_code, 404)

    def test_the_form_is_told_about_the_toggle(self):
        """The answer is the toggle, not another order: both forms can
        hold both books, because the save sends each line to its own
        book's order."""
        d = json.loads(self._resolve("E-0001", book=self.laleli.pk).content)
        self.assertIn("Ergene Fabric", d["error"])
        self.assertIn("other books", d["error"])
        self.assertNotIn("separate order", d["error"])

    def test_an_existing_order_is_told_the_same_thing(self):
        """Editing splits too now, so both forms give the same advice.
        This once told an edit that no such order was possible, which was
        true only while an edit refused to split."""
        d = json.loads(self._resolve(
            "E-0001", book=self.laleli.pk, order=99).content)
        self.assertIn("Ergene Fabric", d["error"])
        self.assertIn("other books", d["error"])

    def test_both_messages_are_translated(self):
        """English is the source; Turkish comes from the catalogue. Asked
        of the catalogue rather than of a response, the way this project's
        other language test does — a live request picks its language from
        middleware, which would answer a question nobody asked."""
        from django.utils import translation
        touched = [
            "That barcode is on %(book)s's shelf. Tick “Show stock from my "
            "other books” to add it — the order is split by book when you save.",
        ]
        with translation.override("tr"):
            missing = [t for t in touched if translation.gettext(t) == t]
        self.assertEqual(missing, [], "no Turkish for: " + repr(missing))

    def test_it_names_the_book_instead_of_denying_the_barcode(self):
        """"No such barcode" is true of this shelf and useless to someone
        holding the roll. Name the book and the dead end becomes an
        instruction."""
        for resp in (self._resolve("E-0001", book=self.laleli.pk),
                     self._check("E-0001", E_SKU, book=self.laleli.pk)):
            d = json.loads(resp.content)
            self.assertEqual(d.get("kind"), "wrong_book")
            self.assertIn("Ergene Fabric", d["error"])
            self.assertNotIn("bulunamad", d["error"])

    # ── what must keep working ──────────────────────────────────────
    def test_the_working_book_still_scans(self):
        resp = self._resolve("L-0001", book=self.laleli.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["roll"]["book_id"], self.laleli.pk)

    def test_the_toggle_reopens_the_other_book(self):
        """With the toggle on, the create form MAY reach both — the save
        splits, so the line it mints is saveable."""
        resp = self._resolve("E-0001", book=self.laleli.pk, cross_book="1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["roll"]["book_id"], self.ergene.pk)

    def test_a_genuinely_unknown_barcode_still_says_not_found(self):
        resp = self._resolve("NO-SUCH-CODE", book=self.laleli.pk)
        self.assertEqual(resp.status_code, 404)
        self.assertNotEqual(json.loads(resp.content).get("kind"), "wrong_book")

    # ── the form asks for that scope ────────────────────────────────
    def test_every_picker_fetch_carries_its_scope(self):
        """Guards the client half: the endpoints only narrow when the
        form tells them which book, so a call site that forgets is the
        bug all over again."""
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
