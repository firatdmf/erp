"""Where the order search gets the price it shows.

A price is worked out from cost: plus a third (or the group's margin),
rounded up to 0.05 — marketing/pricing.py, decided 2026-10-15. On an order
the cost is what the WORKING book's stock of the variant cost, valued as
that book's balance sheet carries it: the line is billed to one book and
ships off that book's shelves, and Laleli's rolls and Ergene's were bought
separately, at their own prices.

Without stock in the working book, the highest cost another book holds it
at; with no valued stock anywhere, the shelf's own figure; last, the
variant's own cost. Staff see each shelf's cost on its chip; a sales rep
sees prices only.

Run with:
    python manage.py test operating.tests.test_search_price_source
"""
import re
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from marketing.models import Product, ProductCategory, ProductVariant

from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem

SKU = "K24644.G07"


def row_for(body, sku):
    for m in re.finditer(r"<li[^>]*>(.*?)</li>", body, re.S):
        row = " ".join(re.sub(r"<[^>]+>", " ", m.group(1)).split())
        if sku in row:
            return row
    return ""


class ThePriceComesOffTheBooksStock(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.product = Product.objects.create(title="Krep", sku="K24644", category=ProductCategory.objects.get_or_create(name="fabric", defaults={"price_multiplier": "4/3"})[0])
        self.variant = ProductVariant.objects.create(
            product=self.product, variant_sku=SKU, variant_cost=Decimal("88.00"))
        self.wh = Warehouse.objects.create(
            name="Laleli depo", accounting_book=self.book)

        User = get_user_model()
        user = User.objects.create_superuser("seller", "s@t.com", "pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _shelf(self, name, **kwargs):
        wh, _ = Warehouse.objects.get_or_create(
            name=name, defaults={"accounting_book": self.book})
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name="Krep", sku=SKU, quantity=Decimal("50"),
            catalog_variant=self.variant, **kwargs)
        WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
            barcode=f"B-{wp.pk}", status="in_stock")
        return wp

    def _member_of(self, *books):
        """A user assigned the books named, so the search may reach them."""
        User = get_user_model()
        u = User.objects.create_superuser(
            f"seller{User.objects.count()}", "s2@t.com", "pw")
        u.member.books.add(self.book, *books)
        u.member.default_book = self.book
        u.member.save()
        return u

    def _search(self):
        return self.client.get(
            reverse("operating:product_autocomplete"),
            {"product": "Krep", "book": self.book.pk}).content.decode()

    def test_the_price_is_the_books_cost_plus_a_third(self):
        self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        row = row_for(self._search(), SKU)
        self.assertIn("$3.20", row)           # 2.40 + a third
        self.assertNotIn("Cost", row.replace("$2.40", ""))  # a price, not a cost
        self.assertNotIn("88", row)           # the variant's stored cost

    def test_a_typed_price_no_longer_counts(self):
        self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        self.variant.variant_price = Decimal("6.50")
        self.variant.save(update_fields=["variant_price"])
        row = row_for(self._search(), SKU)
        self.assertIn("$3.20", row)
        self.assertNotIn("6.50", row)

    def test_every_shelf_still_shows_its_own_cost(self):
        self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        self._shelf("Laleli depo 2", cost_usd=Decimal("3.10"))
        row = row_for(self._search(), SKU)
        self.assertIn("$2.40", row)
        self.assertIn("$3.10", row)

    def _ergene(self, *costs):
        other = Book.objects.create(name="Ergene Fabric")
        for i, cost in enumerate(costs):
            wh = Warehouse.objects.create(name=f"Ergene depo {i}", accounting_book=other)
            wp = WarehouseProduct.objects.create(
                warehouse=wh, name="Krep", sku=SKU, quantity=Decimal("50"),
                catalog_variant=self.variant, cost_usd=Decimal(cost))
            WarehouseProductItem.objects.create(
                product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
                barcode=f"B-E{wp.pk}", status="in_stock")
        self.client.force_login(self._member_of(other))
        return other

    def _price_in(self, book):
        body = self.client.get(
            reverse("operating:product_autocomplete"),
            {"product": "Krep", "book": book.pk, "cross_book": "1"}).content.decode()
        return re.search(r",([0-9.]+),'", body.split(SKU, 1)[1]).group(1)

    def test_each_book_prices_from_its_own_stock(self):
        """Laleli's $2.40 rolls and Ergene's $4.50 ones: two prices."""
        self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        other = self._ergene("4.50")
        self.assertEqual(self._price_in(self.book), "3.20")
        self.assertEqual(self._price_in(other), "6.00")

    def test_a_book_holding_none_takes_the_highest_other_books_cost(self):
        """Overstating cost loses a little margin; understating sells below it."""
        self._ergene("4.50", "5.20")
        # Ergene's stock averages 4.85 → 6.4667 → 6.50.
        self.assertEqual(self._price_in(self.book), "6.50")

    def test_a_shelf_priced_in_another_currency_is_converted(self):
        self._shelf("Laleli depo", purchase_price=Decimal("5.00"),
                    purchase_currency="USD")
        self.assertIn("$6.70", row_for(self._search(), SKU))   # 5.00 → 6.6667

    def test_with_no_stock_cost_the_variants_own_prices_it(self):
        self._shelf("Laleli depo")
        self.assertIn("$117.35", row_for(self._search(), SKU))  # 88.00 → 117.3333

    def test_the_price_is_rounded_up_to_five_cents(self):
        self._shelf("Laleli depo", cost_usd=Decimal("2.4567"))
        row = row_for(self._search(), SKU)
        self.assertIn("$3.30", row)           # 3.2756
        self.assertNotIn("3.2756", row)

    def test_the_rate_is_not_fetched_once_per_row(self):
        """unit_cost_usd() looks up USD/TRY every call; on a 60-row page
        that is 60 lookups for one number."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        for i in range(6):
            self._shelf(f"depo {i}", purchase_price=Decimal("100"),
                        purchase_currency="TRY")
        with CaptureQueriesContext(connection) as ctx:
            self._search()
        self.assertLess(len(ctx.captured_queries), 25,
                        "the search grew a per-row query")

    def test_the_barcode_lookup_prices_from_the_rolls_book(self):
        import json
        wp = self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        data = json.loads(self.client.get(
            reverse("operating:order_create_barcode_resolve"),
            {"barcode": f"B-{wp.pk}"}).content)
        self.assertTrue(data["ok"], data)
        self.assertEqual(data["price"], 3.20)
        self.assertFalse(data["is_cost"])


class ASalesRepSeesPricesOnly(ThePriceComesOffTheBooksStock):
    """The same prices; no shelf costs on the chips."""

    def setUp(self):
        super().setUp()
        from authentication.models import Permission
        User = get_user_model()
        rep = User.objects.create_user("rep_search", password="pw")
        rep.member.books.add(self.book)
        rep.member.default_book = self.book
        rep.member.save()
        perm, _ = Permission.objects.get_or_create(name="sales_rep")
        rep.member.permissions.add(perm)
        self.client.force_login(rep)

    def test_every_shelf_still_shows_its_own_cost(self):
        self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        self._shelf("Laleli depo 2", cost_usd=Decimal("2.16"))
        body = self._search()
        self.assertNotIn("2.40", body)
        self.assertNotIn("2.16", body)
