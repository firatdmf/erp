"""The order form only offers stock the working book owns.

The product search and the two barcode endpoints read every warehouse
in the install. Stock belongs to the book that owns its warehouse, so
offering a line off another book's shelf promises a different
business's asset — and the order would bill it to this book's cari.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from marketing.models import Product, ProductVariant

from .models import Warehouse, WarehouseProduct, WarehouseProductRoll


class PickerSeesOnlyItsOwnBooksShelves(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")

        self.their_roll = self._stock(self.laleli, "GIZLI KUMAS", "BC-LALELI")
        self.my_roll = self._stock(self.ergene, "GIZLI TUL", "BC-ERGENE")

        User = get_user_model()
        self.outsider = User.objects.create_user("ergene_only", password="pw")
        self.outsider.member.books.add(self.ergene)
        self.outsider.member.default_book = self.ergene
        self.outsider.member.save()
        self.client.force_login(self.outsider)

    def _stock(self, book, name, barcode):
        wh = Warehouse.objects.create(name=f"{book.name} depo", accounting_book=book)
        product = Product.objects.create(title=name, sku=f"SKU-{book.pk}")
        variant = ProductVariant.objects.create(
            product=product, variant_sku=f"V-{book.pk}")
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name=name, sku=f"SKU-{book.pk}",
            quantity=Decimal("50"), catalog_variant=variant)
        return WarehouseProductRoll.objects.create(
            product=wp, meters=Decimal("50"), meters_remaining=Decimal("50"),
            barcode=barcode, status="in_stock")

    def _search(self, term):
        return self.client.get(
            reverse("operating:product_autocomplete"), {"product": term}
        ).content.decode()

    def test_the_search_hides_another_books_warehouse_stock(self):
        self.assertNotIn("GIZLI KUMAS", self._search("GIZLI"))

    def test_the_search_still_offers_its_own(self):
        self.assertIn("GIZLI TUL", self._search("GIZLI"))

    def test_a_barcode_from_another_book_does_not_resolve(self):
        resp = self.client.get(
            reverse("operating:order_create_barcode_resolve"),
            {"barcode": self.their_roll.barcode})
        self.assertEqual(resp.status_code, 404)

    def test_its_own_barcode_still_resolves(self):
        resp = self.client.get(
            reverse("operating:order_create_barcode_resolve"),
            {"barcode": self.my_roll.barcode})
        self.assertEqual(resp.status_code, 200)

    def test_the_barcode_check_is_restricted_too(self):
        resp = self.client.get(
            reverse("operating:order_create_barcode_check"),
            {"barcode": self.their_roll.barcode,
             "sku": self.their_roll.product.catalog_variant.variant_sku})
        self.assertEqual(resp.status_code, 404)

    def test_a_book_parameter_cannot_widen_past_the_assignment(self):
        """The form names its book in the query string, so the server
        treats it as a narrowing hint only — asking for a book you are
        not assigned must not open it."""
        html = self.client.get(
            reverse("operating:product_autocomplete"),
            {"product": "GIZLI", "book": str(self.laleli.pk)}).content.decode()
        self.assertNotIn("GIZLI KUMAS", html)
