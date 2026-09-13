"""Where the order search gets the money it shows.

The selling price comes from the catalog, which is the only place a
selling price exists. The COST underneath it — the amber figure shown
when no selling price has been set — now comes from the WAREHOUSE, not
from the catalog's own `cost` column.

That column is a number nobody maintains: it is set once, by hand, and
then the same fabric is bought again at a different price and it says
nothing true. The shelf's cost is stamped when the goods are received,
and is what those metres actually cost. If the figure is going to be
typed into an order and quoted at a customer, it should be the one that
came from a purchase.

Run with:
    python manage.py test operating.test_search_price_source
"""
import re
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from marketing.models import Product, ProductVariant

from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem

SKU = "K24644.G07"


def row_for(body, sku):
    for m in re.finditer(r"<li[^>]*>(.*?)</li>", body, re.S):
        row = " ".join(re.sub(r"<[^>]+>", " ", m.group(1)).split())
        if sku in row:
            return row
    return ""


class TheCostComesOffTheShelf(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        # A catalog cost that is WRONG, to prove nothing reads it.
        self.product = Product.objects.create(
            title="Krep", sku="K24644", cost=Decimal("99.00"))
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

    def test_it_shows_what_the_shelf_cost_not_the_catalog(self):
        self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        row = row_for(self._search(), SKU)
        self.assertIn("$2.40", row)
        self.assertIn("Cost", row)
        self.assertNotIn("88", row)   # the variant's catalog cost
        self.assertNotIn("99", row)   # the product's catalog cost

    def test_a_selling_price_still_wins(self):
        self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        self.variant.variant_price = Decimal("6.50")
        self.variant.save(update_fields=["variant_price"])
        row = row_for(self._search(), SKU)
        self.assertIn("$6.50", row)
        self.assertNotIn("Cost", row)

    def test_every_shelf_shows_its_own_cost(self):
        """Shelves disagree because two businesses each bought the
        fabric — 48 variants in this catalogue do. One number in the
        corner has to pick a side and then says nothing about the other,
        so each chip carries the cost of the metres beside it."""
        self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        self._shelf("Laleli depo 2", cost_usd=Decimal("3.10"))
        row = row_for(self._search(), SKU)
        self.assertIn("$2.40", row)
        self.assertIn("$3.10", row)

    def test_the_prefill_is_the_working_book_s_cost(self):
        """The line is billed to one book and ships off that book's
        shelf, so the other business's cost describes stock this line is
        not going to move."""
        other = Book.objects.create(name="Ergene Fabric")
        self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        wh = Warehouse.objects.create(name="Ergene depo", accounting_book=other)
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name="Krep", sku=SKU, quantity=Decimal("50"),
            catalog_variant=self.variant, cost_usd=Decimal("4.50"))
        WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
            barcode="B-E1", status="in_stock")
        self.client.force_login(self._member_of(other))

        # Working in Laleli: its own $2.40 wins, though $4.50 is higher.
        body = self.client.get(
            reverse("operating:product_autocomplete"),
            {"product": "Krep", "book": self.book.pk, "cross_book": "1"}).content.decode()
        self.assertTrue(row_for(body, SKU).rstrip().endswith("$2.40 Cost"),
                        row_for(body, SKU))

        # Working in Ergene: its own $4.50.
        body = self.client.get(
            reverse("operating:product_autocomplete"),
            {"product": "Krep", "book": other.pk, "cross_book": "1"}).content.decode()
        self.assertTrue(row_for(body, SKU).rstrip().endswith("$4.50 Cost"),
                        row_for(body, SKU))

    def test_it_falls_back_to_the_highest_when_this_book_holds_none(self):
        """Safe direction for a figure about to be quoted: overstating
        cost loses a little margin, understating sells below it."""
        other = Book.objects.create(name="Ergene Fabric")
        for name, cost in (("Ergene depo", "4.50"), ("Ergene depo 2", "5.20")):
            wh = Warehouse.objects.create(name=name, accounting_book=other)
            wp = WarehouseProduct.objects.create(
                warehouse=wh, name="Krep", sku=SKU, quantity=Decimal("50"),
                catalog_variant=self.variant, cost_usd=Decimal(cost))
            WarehouseProductItem.objects.create(
                product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
                barcode=f"B-{wp.pk}", status="in_stock")
        self.client.force_login(self._member_of(other))
        body = self.client.get(
            reverse("operating:product_autocomplete"),
            {"product": "Krep", "book": self.book.pk, "cross_book": "1"}).content.decode()
        self.assertTrue(row_for(body, SKU).rstrip().endswith("$5.20 Cost"),
                        row_for(body, SKU))

    def test_a_priced_row_does_not_advertise_its_cost(self):
        """Costs ride the chips only where the row is quoting one, so an
        ordinary row neither gains clutter nor starts showing margins."""
        self._shelf("Laleli depo", cost_usd=Decimal("2.40"))
        self.variant.variant_price = Decimal("6.50")
        self.variant.save(update_fields=["variant_price"])
        row = row_for(self._search(), SKU)
        self.assertIn("$6.50", row)
        self.assertNotIn("2.40", row)

    def test_a_shelf_priced_in_another_currency_is_converted(self):
        self._shelf("Laleli depo", purchase_price=Decimal("5.00"),
                    purchase_currency="USD")
        self.assertIn("$5.00", row_for(self._search(), SKU))

    def test_a_shelf_that_knows_no_cost_shows_nothing_rather_than_guess(self):
        """No cost_usd, no purchase price. The catalog's number is not a
        stand-in — that is the whole point of this change."""
        self._shelf("Laleli depo")
        row = row_for(self._search(), SKU)
        self.assertIn("$0", row)
        self.assertNotIn("88", row)

    def test_the_cost_is_shown_to_the_cent(self):
        """Shelf costs are stored to four places for valuation. A price
        someone is about to be quoted is money."""
        self._shelf("Laleli depo", cost_usd=Decimal("2.4567"))
        row = row_for(self._search(), SKU)
        self.assertIn("$2.46", row)
        self.assertNotIn("2.4567", row)

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
