"""The order form's stock item picker: oldest day first, then barcode,
and only its own shelf.

Run with:
    python manage.py test operating.test_roll_picker_order
"""
import datetime
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

    def test_within_one_day_the_barcode_decides(self):
        """A stock count enters a shelf in whatever order the rolls were
        picked up, so the minute is noise; the label sequence is not."""
        start = self._aged(7)
        wp = self._shelf(self.ergene, Decimal("2.40"))
        for minutes, barcode in ((0, "LZK0300003495"), (1, "LZK0300003492"),
                                 (26, "LZK0300003070"), (60, "LZK0300003478")):
            self._top(wp, barcode, scanned=start + datetime.timedelta(minutes=minutes))
        self.assertEqual([r["barcode"] for r in self._list()],
                         ["LZK0300003070", "LZK0300003478",
                          "LZK0300003492", "LZK0300003495"])

    def test_an_earlier_day_beats_a_lower_barcode(self):
        wp = self._shelf(self.ergene, Decimal("2.40"))
        self._top(wp, "LZK0300003001", scanned=self._aged(1))
        self._top(wp, "LZK0300003999", scanned=self._aged(30))
        self.assertEqual([r["barcode"] for r in self._list()],
                         ["LZK0300003999", "LZK0300003001"])

    def test_price_breaks_a_tie_between_unlabelled_items(self):
        same = self._aged(7)
        dear = self._top(self._shelf(self.ergene, Decimal("2.40")), None, scanned=same)
        cheap = self._top(self._shelf(self.ergene, Decimal("2.16")), None, scanned=same)
        self.assertEqual([r["id"] for r in self._list()], [cheap.pk, dear.pk])

    def test_a_stock_item_with_no_cost_sorts_last_on_a_tie(self):
        same = self._aged(7)
        unknown = self._top(self._shelf(self.ergene, None), None, scanned=same)
        priced = self._top(self._shelf(self.ergene, Decimal("2.40")), None, scanned=same)
        self.assertEqual([r["id"] for r in self._list()], [priced.pk, unknown.pk])

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

    # --- cost -------------------------------------------------------
    def test_each_item_carries_its_cost_per_metre(self):
        self._top(self._shelf(self.ergene, Decimal("2.40")), "BC-PRICED")
        self._top(self._shelf(self.ergene, None), "BC-UNKNOWN")
        resp = self.client.get(reverse("operating:order_create_roll_list"), {"sku": SKU})
        data = json.loads(resp.content)
        self.assertEqual({r["barcode"]: r["unit_cost"] for r in data["rolls"]},
                         {"BC-PRICED": 2.40, "BC-UNKNOWN": None})
        self.assertTrue(data["cost_symbol"])

    def test_a_sales_rep_is_sent_the_marked_up_price_not_the_cost(self):
        from authentication.models import Permission
        perm, _ = Permission.objects.get_or_create(name="sales_rep")
        self.user.member.permissions.add(perm)
        self._top(self._shelf(self.ergene, Decimal("2.40")), "BC-PRICED")
        resp = self.client.get(reverse("operating:order_create_roll_list"), {"sku": SKU})
        data = json.loads(resp.content)
        self.assertEqual([r["barcode"] for r in data["rolls"]], ["BC-PRICED"])
        self.assertNotIn("unit_cost", data["rolls"][0])
        # 2.40 × 1.10 = 2.64, up to the next 0.05.
        self.assertEqual(data["rolls"][0]["unit_price"], 2.65)

    def test_a_pack_product_is_not_counted_in_metres(self):
        self._top(self._shelf(self.ergene, Decimal("12.00")), "BC-BOX")
        self._top(self._shelf(self.ergene, Decimal("2.40")), "BC-ROLL")
        self.assertEqual({r["unit"] for r in self._list()}, {"m"})
        # The unit is the product's, so every shelf of it follows at once.
        self.variant.product.set_unit("pack", "box")
        self.assertEqual({r["unit"] for r in self._list()}, {"pack"})
