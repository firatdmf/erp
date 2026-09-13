"""What a warehouse counts its stock in, and where that unit shows up.

Every quantity in the warehouse used to be metres — not by choice but by
default: the columns were called `meters`, and every screen printed "m"
after the number. That was harmless while the shelves held nothing but
fabric, and became wrong the moment a pallet of ready-made curtain sets
arrived, because a box of 20 sets is not 20 metres of anything.

`WarehouseProduct.unit` says what the numbers mean. These tests pin the
places that have to read it rather than assume:

* the product rows and the stock-item rows under them
* the warehouse header total, which must NOT claim a unit when the
  warehouse holds more than one
* the printed label
* a move between warehouses, which has to carry the unit with the goods

Run with:
    python manage.py test operating.test_stock_unit
"""
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory

from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


class StockUnitIsShownNotAssumed(TestCase):
    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        self.shop = Warehouse.objects.create(
            name="Ready-made Shop", accounting_book=self.book)

        self.curtains = WarehouseProduct.objects.create(
            warehouse=self.shop, name="Peony 84in", sku="RN1357.RM8",
            quantity=Decimal("20"), unit="pack", pack_type="box")
        WarehouseProductItem.objects.create(
            product=self.curtains, quantity=Decimal("20"),
            quantity_remaining=Decimal("20"), barcode="BOX-12",
            lot_number="12", status="in_stock",
            unit_cost_base=Decimal("15.55"))

        user = get_user_model().objects.create_user("shopkeeper", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _page(self, warehouse=None):
        resp = self.client.get(reverse(
            "operating:warehouse_detail", args=[(warehouse or self.shop).pk]))
        self.assertEqual(resp.status_code, 200)
        return _text(resp.content.decode())

    def test_a_product_row_is_counted_in_its_own_unit(self):
        self.assertIn("20.00 pack", self._page())

    def test_it_does_not_call_curtain_sets_metres(self):
        self.assertNotIn("20.00 m ", self._page())

    def test_the_header_total_carries_the_unit_when_there_is_only_one(self):
        self.assertRegex(self._page(), r"20\s*pack")

    def test_a_mixed_warehouse_claims_no_unit_for_its_total(self):
        """Metres of fabric and boxes of curtains do not add up to anything,
        so the total drops the unit rather than picking one of them. The
        per-product rows still carry their own."""
        WarehouseProduct.objects.create(
            warehouse=self.shop, name="seta grey", sku="SETA-1",
            quantity=Decimal("300"), unit="mt", pack_type="roll")
        page = self._page()
        self.assertNotRegex(page, r"320\s*(pack|m)\b")
        self.assertIn("20.00 pack", page)
        self.assertIn("300.00 m", page)

    def test_the_default_is_metres_so_existing_fabric_is_untouched(self):
        """Every product that existed before the field was added is fabric.
        The default is a statement about the data, not a guess, and a
        product created without saying otherwise still reads as metres."""
        fabric = WarehouseProduct.objects.create(
            warehouse=self.shop, name="grek tul", sku="GT-1",
            quantity=Decimal("48.5"))
        self.assertEqual(fabric.unit, "mt")
        self.assertEqual(fabric.unit_short, "m")

    def test_an_unrecognised_unit_shows_itself_rather_than_vanishing(self):
        odd = WarehouseProduct.objects.create(
            warehouse=self.shop, name="odd", sku="ODD-1",
            quantity=Decimal("1"), unit="yards", pack_type="crate")
        self.assertEqual(odd.unit_short, "yards")


class TheLabelSaysWhatItIsCounting(TestCase):
    """The sticker on the box prints a bare number under "QUANTITY". That
    read as metres to anyone who had only ever seen a roll tag, so the unit
    now goes on it too."""

    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        self.shop = Warehouse.objects.create(
            name="Ready-made Shop", accounting_book=self.book)
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.shop, name="Peony 84in", sku="RN1357.RM8",
            quantity=Decimal("20"), unit="pack", pack_type="box")

        user = get_user_model().objects.create_user("printer", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

        # reportlab flate-compresses page streams by default, which would
        # hide the drawn strings from a byte search. Off for the test only.
        import reportlab.rl_config as rl_config
        self._compression = rl_config.pageCompression
        rl_config.pageCompression = 0
        self.addCleanup(setattr, rl_config, "pageCompression", self._compression)

    def _drawn_strings(self, roll):
        url = reverse("operating:warehouse_product_label", kwargs={
            "warehouse_pk": self.shop.pk, "product_pk": self.wp.pk})
        resp = self.client.get(url, {"roll": roll.pk})
        self.assertEqual(resp.status_code, 200)
        return [s.decode("latin-1")
                for s in re.findall(rb"\((.*?)\)\s*Tj", resp.content)]

    def test_it_prints_packs_not_metres(self):
        roll = WarehouseProductItem.objects.create(
            product=self.wp, quantity=Decimal("20"),
            quantity_remaining=Decimal("20"), barcode="BOX-12")
        drawn = self._drawn_strings(roll)
        self.assertIn("20.00 pack", drawn)
        self.assertNotIn("20.00 m", drawn)


class MovingStockCarriesTheUnit(TestCase):
    """A move creates the destination row from scratch when the SKU is not
    already on that shelf. It used to build it without a unit, so it took
    the model default — and a box of curtain sets moved shelf to shelf came
    out the other side measured in metres."""

    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        self.source = Warehouse.objects.create(
            name="Shop A", accounting_book=self.book)
        self.target = Warehouse.objects.create(
            name="Shop B", accounting_book=self.book)
        self.wp = WarehouseProduct.objects.create(
            warehouse=self.source, name="Peony 84in", sku="RN1357.RM8",
            quantity=Decimal("20"), unit="pack", pack_type="box")
        self.roll = WarehouseProductItem.objects.create(
            product=self.wp, quantity=Decimal("20"),
            quantity_remaining=Decimal("20"), barcode="BOX-12",
            status="in_stock")

        user = get_user_model().objects.create_user("mover", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        user.is_staff = user.is_superuser = True
        user.save()
        self.client.force_login(user)

    def test_the_destination_row_is_counted_the_same_way(self):
        resp = self.client.post(reverse(
            "operating:warehouse_roll_move_here",
            args=[self.target.pk, self.roll.pk]))
        self.assertIn(resp.status_code, (200, 302))

        moved = WarehouseProduct.objects.get(
            warehouse=self.target, sku="RN1357.RM8")
        self.assertEqual(moved.unit, "pack")
        self.assertEqual(moved.unit_short, "pack")


class OneStockItemIsCalledWhatItIs(TestCase):
    """A stock item is a physical lot that arrived together and is picked
    from together. For fabric that is a roll; for ready-made curtains it is
    a box, and `lot_number` literally holds the box number.

    Every warehouse screen said "roll" — the word, the count and the
    scroll icon — because fabric was all the shelves held. So the
    Ready-made Shop listed a box of 20 curtain sets as a roll.
    """

    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        self.shop = Warehouse.objects.create(
            name="Ready-made Shop", accounting_book=self.book)
        self.mill = Warehouse.objects.create(
            name="Laleli Fabrika", accounting_book=self.book)

        self.curtains = WarehouseProduct.objects.create(
            warehouse=self.shop, name="Peony 84in", sku="RN1357.RM8",
            quantity=Decimal("20"), unit="pack", pack_type="box")
        WarehouseProductItem.objects.create(
            product=self.curtains, quantity=Decimal("20"),
            quantity_remaining=Decimal("20"), lot_number="12",
            status="in_stock", unit_cost_base=Decimal("15.55"))

        self.fabric = WarehouseProduct.objects.create(
            warehouse=self.mill, name="seta grey", sku="SETA-1",
            quantity=Decimal("300"))
        WarehouseProductItem.objects.create(
            product=self.fabric, quantity=Decimal("300"),
            quantity_remaining=Decimal("300"), barcode="BC-1",
            status="in_stock", unit_cost_base=Decimal("4"))

        user = get_user_model().objects.create_user("keeper", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _page(self, warehouse, **params):
        resp = self.client.get(reverse(
            "operating:warehouse_detail", args=[warehouse.pk]), params)
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_the_shop_counts_boxes(self):
        self.assertIn("1 box", _text(self._page(self.shop)))

    def test_the_mill_still_counts_rolls(self):
        self.assertIn("1 roll", _text(self._page(self.mill)))

    def test_the_shop_never_says_roll(self):
        self.assertNotRegex(_text(self._page(self.shop)), r"\d+ rolls?\b")

    def test_the_header_icon_follows_the_goods(self):
        """A scroll of cloth and a carton are different pictures, and the
        icon was doing as much of the telling as the word."""
        self.assertRegex(self._page(self.shop),
                         r'<i class="fa fa-box"></i>\s*[\d,]+\s*box')
        self.assertRegex(self._page(self.mill),
                         r'<i class="fa fa-scroll"></i>\s*[\d,]+\s*roll')

    def test_the_grouped_view_agrees_with_the_flat_one(self):
        self.assertIn("1 box", _text(self._page(self.shop, view="grouped")))
        self.assertIn("1 roll", _text(self._page(self.mill, view="grouped")))

    def test_a_warehouse_holding_both_calls_them_items(self):
        """Neither word is true of the whole shelf, so it says neither —
        rather than calling a box of curtains a roll, which is what the
        hardcoded label did."""
        WarehouseProduct.objects.create(
            warehouse=self.shop, name="grek tul", sku="GT-1",
            quantity=Decimal("50"), unit="mt", pack_type="roll")
        page = _text(self._page(self.shop))
        self.assertRegex(page, r"\d+ items\b")
        self.assertNotRegex(page, r"\d+ rolls?\b")

    def test_the_noun_falls_back_rather_than_vanishing(self):
        odd = WarehouseProduct.objects.create(
            warehouse=self.shop, name="odd", sku="ODD-1",
            quantity=Decimal("1"), unit="yards", pack_type="crate")
        self.assertEqual(odd.item_noun, "item")
        self.assertEqual(odd.item_noun_plural, "items")
        self.assertEqual(odd.item_icon, "fa-layer-group")

    def test_the_pack_is_not_a_function_of_the_unit(self):
        """The whole reason these are two fields. Metres can arrive on a
        bolt as readily as a roll, and pieces can come in a bag as readily
        as a box — so setting one must not move the other."""
        bagged = WarehouseProduct.objects.create(
            warehouse=self.shop, name="tape", sku="TP-1",
            quantity=Decimal("500"), unit="mt", pack_type="bag")
        self.assertEqual(bagged.unit_short, "m")
        self.assertEqual(bagged.item_noun_plural, "bags")

        boxed_metres = WarehouseProduct.objects.create(
            warehouse=self.shop, name="trim", sku="TR-1",
            quantity=Decimal("80"), unit="mt", pack_type="box")
        self.assertEqual(boxed_metres.unit_short, "m")
        self.assertEqual(boxed_metres.item_noun_plural, "boxes")


class TheProductPageSpeaksTheProductsLanguage(TestCase):
    """The warehouse list was fixed before this page was, so a curtain
    product's own page still read "20.00 m", "Active rolls" and "Length"
    over a column of box counts."""

    def setUp(self):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=usd)
        self.shop = Warehouse.objects.create(
            name="Ready-made Shop", accounting_book=self.book)
        self.mill = Warehouse.objects.create(
            name="Laleli Fabrika", accounting_book=self.book)

        self.curtains = WarehouseProduct.objects.create(
            warehouse=self.shop, name="Peony 84in", sku="RN1357.RM8",
            quantity=Decimal("20"), unit="pack", pack_type="box")
        WarehouseProductItem.objects.create(
            product=self.curtains, quantity=Decimal("20"),
            quantity_remaining=Decimal("20"), lot_number="12",
            status="in_stock", unit_cost_base=Decimal("15.55"))

        self.fabric = WarehouseProduct.objects.create(
            warehouse=self.mill, name="seta grey", sku="SETA-1",
            quantity=Decimal("300"))
        WarehouseProductItem.objects.create(
            product=self.fabric, quantity=Decimal("300"),
            quantity_remaining=Decimal("300"), barcode="BC-1",
            status="in_stock", unit_cost_base=Decimal("4"))

        user = get_user_model().objects.create_user("reader", password="pw")
        user.member.books.add(self.book)
        user.member.default_book = self.book
        user.member.save()
        self.client.force_login(user)

    def _page(self, product):
        resp = self.client.get(reverse(
            "operating:warehouse_product_detail",
            args=[product.warehouse_id, product.pk]))
        self.assertEqual(resp.status_code, 200)
        return _text(resp.content.decode())

    def test_the_curtain_page_counts_packs_and_boxes(self):
        page = self._page(self.curtains)
        self.assertIn("20.00 pack", page)
        self.assertIn("Active boxes", page)

    def test_the_curtain_page_never_prints_a_metre(self):
        self.assertNotRegex(self._page(self.curtains), r"\d+\.\d\d m\b")

    def test_the_quantity_column_is_not_headed_length_for_boxes(self):
        """Metres of cloth are a length and kilos are a weight. A count of
        curtain sets is neither, so "Length: 20" over a box of them is
        simply a false statement."""
        self.assertEqual(self.curtains.quantity_label, "Quantity")
        self.assertEqual(self.fabric.quantity_label, "Length")

    def test_the_fabric_page_is_unchanged(self):
        page = self._page(self.fabric)
        self.assertIn("300.00 m", page)
        self.assertIn("Active rolls", page)
        self.assertNotIn("Active boxes", page)

    def test_a_product_sold_by_weight_says_weight(self):
        bale = WarehouseProduct.objects.create(
            warehouse=self.mill, name="waste", sku="W-1",
            quantity=Decimal("5"), unit="kg", pack_type="bale")
        self.assertEqual(bale.quantity_label, "Weight")
        self.assertEqual(bale.item_noun_plural, "bales")
