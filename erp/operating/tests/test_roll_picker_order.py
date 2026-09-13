"""The order form's stock item picker: FIFO, and only its own shelf.

Run with:
    python manage.py test operating.test_roll_picker_order
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

SKU = "K24593.G07"


class RollPicker(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.laleli = Book.objects.create(name="Laleli Fabric")

        product = Product.objects.create(title="GREK TÜL", sku=SKU)
        self.variant = ProductVariant.objects.create(
            product=product, variant_sku=SKU)

        User = get_user_model()
        self.user = User.objects.create_user("picker", password="pw")
        self.user.member.books.add(self.ergene)
        self.user.member.default_book = self.ergene
        self.user.member.save()
        self.client.force_login(self.user)

    def _shelf(self, book, cost):
        # Warehouse.name is unique install-wide, and a test that stands the
        # same SKU on two shelves of one book needs two names.
        self._shelf_no = getattr(self, "_shelf_no", 0) + 1
        wh = Warehouse.objects.create(
            name=f"{book.name} depo {self._shelf_no}", accounting_book=book)
        return WarehouseProduct.objects.create(
            warehouse=wh, name="GREK TÜL", sku=SKU, quantity=Decimal("0"),
            cost_usd=cost, catalog_variant=self.variant)

    def _top(self, wp, barcode, scanned=None):
        roll = WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("20"), quantity_remaining=Decimal("20"),
            barcode=barcode, status="in_stock")
        if scanned is not None:
            WarehouseProductItem.objects.filter(pk=roll.pk).update(
                scanned_at=scanned)
        return roll

    def _list(self, **extra):
        resp = self.client.get(
            reverse("operating:order_create_roll_list"),
            {"sku": SKU, **extra})
        self.assertEqual(resp.status_code, 200)
        return json.loads(resp.content)["rolls"]

    # --- ordering ---------------------------------------------------
    def _aged(self, days):
        import datetime

        from django.utils import timezone
        return timezone.now() - datetime.timedelta(days=days)

    def test_the_oldest_stock_item_comes_first(self):
        wp = self._shelf(self.ergene, Decimal("2.40"))
        self._top(wp, "BC-NEW", scanned=self._aged(1))
        self._top(wp, "BC-OLD", scanned=self._aged(30))
        self.assertEqual([r["barcode"] for r in self._list()],
                         ["BC-OLD", "BC-NEW"])

    def test_age_beats_price(self):
        """Draining the cheap stock items first would let the picking order set
        the margin. Stock items of one SKU are interchangeable, so the old dear
        one goes before the new cheap one."""
        self._top(self._shelf(self.ergene, Decimal("2.40")), "BC-OLD-DEAR",
                  scanned=self._aged(30))
        self._top(self._shelf(self.ergene, Decimal("2.16")), "BC-NEW-CHEAP",
                  scanned=self._aged(1))
        self.assertEqual([r["barcode"] for r in self._list()],
                         ["BC-OLD-DEAR", "BC-NEW-CHEAP"])

    def test_price_breaks_a_tie_on_age(self):
        same = self._aged(7)
        self._top(self._shelf(self.ergene, Decimal("2.40")), "BC-DEAR",
                  scanned=same)
        self._top(self._shelf(self.ergene, Decimal("2.16")), "BC-CHEAP",
                  scanned=same)
        self.assertEqual([r["barcode"] for r in self._list()],
                         ["BC-CHEAP", "BC-DEAR"])

    def test_a_stock_item_with_no_cost_sorts_last_on_a_tie(self):
        same = self._aged(7)
        self._top(self._shelf(self.ergene, None), "BC-UNKNOWN", scanned=same)
        self._top(self._shelf(self.ergene, Decimal("2.40")), "BC-PRICED",
                  scanned=same)
        self.assertEqual([r["barcode"] for r in self._list()],
                         ["BC-PRICED", "BC-UNKNOWN"])

    # --- book scope -------------------------------------------------
    def test_another_books_shelf_is_not_offered(self):
        """The picker's two siblings narrow to the working book; this one
        did not, so it offered another business's shelf to anyone who
        knew the SKU."""
        self._top(self._shelf(self.laleli, Decimal("2.16")), "BC-THEIRS")
        self._top(self._shelf(self.ergene, Decimal("2.40")), "BC-MINE")
        self.assertEqual([r["barcode"] for r in self._list()], ["BC-MINE"])

    def test_a_book_parameter_cannot_widen_past_the_assignment(self):
        self._top(self._shelf(self.laleli, Decimal("2.16")), "BC-THEIRS")
        self._top(self._shelf(self.ergene, Decimal("2.40")), "BC-MINE")
        self.assertEqual(
            [r["barcode"] for r in self._list(book=str(self.laleli.pk))], [])
