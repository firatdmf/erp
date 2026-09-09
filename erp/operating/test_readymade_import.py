"""The ready-made curtain stock import, end to end.

The command writes 2,835 curtain sets worth ~$50,000 onto a shelf that
counts in packs rather than metres, and the balance sheet picks that up
the moment the rows exist. These tests build a miniature of the real
workbooks and drive the actual command over them.

What is being pinned:

* a row becomes a stock item in the box it was counted in, so a picker
  knows which box to open
* the same SKU in two boxes is two stock items, not one merged row
* the printed EAN lands on the PRODUCT, and the stock item's own barcode
  stays null — identical sets cannot share a unique column
* the colour word is ignored when a design has only one colourway, and
  consulted when it has two
* a row whose length is unreadable is left on the floor, not guessed at
* re-running adds nothing, and --undo takes it back out

Run with:
    python manage.py test operating.test_readymade_import
"""
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from accounting.models import Book, CurrencyCategory
from marketing.models import Product, ProductCategory, ProductVariant
from operating.models import (StockMovement, Warehouse, WarehouseProduct,
                              WarehouseProductItem)

# (design, colour, length, header, sets, price, barcode) for the spec sheet.
# Dandelion is made in two grommet colourways and one rod-pocket one, so it
# exercises both the tie-break and the single-colourway path. Peony has a
# single colourway whose name matches no warehouse colour word at all.
#
# The warehouse writes Şampanya as "KREM" — the sheet only ever uses BEYAZ,
# KREM, D BEYAZ and TURKUAZ, never the spec's own colourway names.
SPEC_ROWS = [
    ("RK72010", "Beyaz", 84, "Grommet", "712179795150"),
    ("RK72010", "Şampanya", 84, "Grommet", "712179795167"),
    ("K72010", "Turkuaz", 84, "Rod Pocket", "712179795198"),
    ("R1357", "Mürdüm (Altın & Mirle)", 84, "Rod Pocket", "712179795327"),
]

# (box, design, length, colour, header, sets, price) for the stock sheet.
STOCK_ROWS = [
    (12, 1357, 84, "KREM", "CEPLİ", 20, 15.55),      # colour word ignored
    (13, 1357, 84, "KREM", "CEPLİ", 18, 15.55),      # same SKU, second box
    (14, 72010, 84, "BEYAZ", "HALKALI", 10, 19.50),  # tie broken by colour
    (None, 72010, 84, "KREM", "HALKALI", 5, 19.50),  # unnamed -> box 14
    (15, 72010, 84, "TURKUAZ", "CEPLİ", 7, 18.10),
    (16, 1357, "*", "KREM", "CEPLİ", 3, 15.55),      # unreadable length
]


def _write_spec(path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Desen", "Renk", "Uzunluk (inç)", "En (inç)", "Yan Dikiş (cm)",
               "Tip", "Header", "Header (cm)", "Pocket (cm)", "Adet", "Price",
               "Barkod No"])
    for design, colour, length, kind, barcode in SPEC_ROWS:
        ws.append([design, colour, length, 53, 2.5, kind, "-", "-", "-",
                   98, 15.55, int(barcode)])
    wb.save(path)


def _write_stock(path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "GÜNCEL"
    ws.append(["index", "KUTU", "DESEN", "ÖLÇÜ", "RENK", "ASMA TİPİ",
               "KAP İÇİ SET ADET", "FİYAT/ADET", "FİYAT TOPLAM"])
    for i, (box, design, length, colour, header, sets, price) in enumerate(STOCK_ROWS):
        ws.append([i, box, design, length, colour, header, sets, price,
                   sets * price])
    # The real sheet ends with a TOTAL row, which must not be read as stock.
    ws.append([len(STOCK_ROWS), "TOTAL", None, None, None, None,
               sum(r[5] for r in STOCK_ROWS), None, 0])
    wb.save(path)


class ReadymadeStockImport(TestCase):
    @classmethod
    def setUpTestData(cls):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        Book.objects.create(name="Ergene Fabric", base_currency=usd)
        category = ProductCategory.objects.create(name="ready-made_curtain")

        dandelion = Product.objects.create(
            title="Dandelion", sku="RK72010", category=category)
        for suffix in ("GW8", "GC8", "RT8"):
            ProductVariant.objects.create(
                product=dandelion, variant_sku=f"RK72010.{suffix}")
        peony = Product.objects.create(
            title="Peony", sku="RN1357", category=category)
        ProductVariant.objects.create(product=peony, variant_sku="RN1357.RM8")

    def setUp(self):
        self._dir = TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.spec = Path(self._dir.name) / "spec.xlsx"
        self.stock = Path(self._dir.name) / "stock.xlsx"
        _write_spec(self.spec)
        _write_stock(self.stock)

    def _run(self, *extra):
        out = StringIO()
        call_command("import_readymade_stock", "--stock", str(self.stock),
                     "--spec", str(self.spec), *extra, stdout=out, stderr=out)
        return out.getvalue()

    def _apply(self):
        return self._run("--apply")

    # ── the shelf ──────────────────────────────────────────────────────
    def test_a_dry_run_writes_nothing(self):
        self._run()
        self.assertFalse(Warehouse.objects.filter(
            name="Ready-made Shop").exists())

    def test_it_creates_the_shop_under_the_ergene_book(self):
        self._apply()
        shop = Warehouse.objects.get(name="Ready-made Shop")
        self.assertEqual(shop.accounting_book.name, "Ergene Fabric")

    def test_the_shop_counts_in_packs_not_metres(self):
        self._apply()
        for wp in WarehouseProduct.objects.all():
            self.assertEqual(wp.unit, "paket")
            self.assertEqual(wp.unit_short, "pack")

    def test_the_sets_are_packed_in_boxes(self):
        """Counted in packs, packed in boxes — two separate facts, and the
        import states both rather than inferring one."""
        self._apply()
        for wp in WarehouseProduct.objects.all():
            self.assertEqual(wp.pack_type, "box")
            self.assertEqual(wp.item_noun_plural, "boxes")

    # ── boxes ──────────────────────────────────────────────────────────
    def test_each_row_becomes_a_stock_item_in_its_own_box(self):
        self._apply()
        peony = WarehouseProduct.objects.get(sku="RN1357.RM8")
        boxes = dict(peony.stock_items.values_list("lot_number", "quantity"))
        self.assertEqual(boxes, {"12": Decimal("20.00"), "13": Decimal("18.00")})

    def test_the_same_sku_in_two_boxes_stays_two_stock_items(self):
        self._apply()
        peony = WarehouseProduct.objects.get(sku="RN1357.RM8")
        self.assertEqual(peony.stock_items.count(), 2)
        self.assertEqual(peony.quantity, Decimal("38.00"))

    def test_a_row_with_no_box_number_joins_the_box_above_it(self):
        """The sheet leaves KUTU blank when a box holds several designs, so
        the reader carries the last number down. Without that, five sets of
        Şampanya would be filed under no box at all."""
        self._apply()
        wp = WarehouseProduct.objects.get(sku="RK72010.GC8")
        item = wp.stock_items.get()
        self.assertEqual(item.lot_number, "14")

    # ── barcodes ───────────────────────────────────────────────────────
    def test_the_ean_goes_on_the_product(self):
        self._apply()
        self.assertEqual(
            WarehouseProduct.objects.get(sku="RK72010.GW8").barcode,
            "712179795150")

    def test_the_stock_items_own_barcode_stays_null(self):
        """Identical sets share one printed EAN and the column is UNIQUE, so
        it cannot hold it. Scanning resolves through the product instead."""
        self._apply()
        self.assertEqual(
            list(WarehouseProductItem.objects.values_list("barcode", flat=True)),
            [None] * WarehouseProductItem.objects.count())

    # ── matching ───────────────────────────────────────────────────────
    def test_the_colour_word_is_ignored_when_there_is_only_one_colourway(self):
        """A Peony box is written up as KREM; Peony is only made in Mürdüm.
        The sheet's word is decorative and must not decide anything."""
        self._apply()
        self.assertTrue(
            WarehouseProduct.objects.filter(sku="RN1357.RM8").exists())

    def test_the_colour_word_decides_when_a_design_has_two_colourways(self):
        self._apply()
        self.assertEqual(
            WarehouseProduct.objects.get(sku="RK72010.GW8").stock_items.get().quantity,
            Decimal("10.00"))
        self.assertEqual(
            WarehouseProduct.objects.get(sku="RK72010.GC8").stock_items.get().quantity,
            Decimal("5.00"))

    def test_the_header_separates_two_colourways_of_one_design(self):
        self._apply()
        rod = WarehouseProduct.objects.get(sku="RK72010.RT8")
        self.assertEqual(rod.stock_items.get().quantity, Decimal("7.00"))

    def test_an_unreadable_length_is_left_on_the_floor(self):
        out = self._apply()
        self.assertEqual(WarehouseProductItem.objects.count(), 5)
        self.assertIn("length unreadable", out)
        self.assertNotIn(Decimal("3.00"), [
            i.quantity for i in WarehouseProductItem.objects.all()])

    def test_the_total_row_is_not_read_as_stock(self):
        self._apply()
        self.assertEqual(
            WarehouseProductItem.objects.count(), len(STOCK_ROWS) - 1)

    # ── money ──────────────────────────────────────────────────────────
    def test_each_stock_item_is_stamped_with_what_it_cost(self):
        self._apply()
        item = WarehouseProduct.objects.get(
            sku="RN1357.RM8").stock_items.first()
        self.assertEqual(item.unit_cost_base, Decimal("15.5500"))

    def test_the_shop_is_worth_what_the_sheet_says(self):
        self._apply()
        shop = Warehouse.objects.get(name="Ready-made Shop")
        expected = sum(
            (Decimal(str(sets)) * Decimal(str(price))
             for _b, _d, length, _c, _h, sets, price in STOCK_ROWS
             if length != "*"), Decimal("0"))
        self.assertEqual(shop.total_value_usd(), expected)

    # ── re-running ─────────────────────────────────────────────────────
    def test_running_it_twice_adds_nothing(self):
        self._apply()
        before = list(WarehouseProductItem.objects.values_list("pk", flat=True))
        quantities = {wp.pk: wp.quantity for wp in WarehouseProduct.objects.all()}
        out = self._apply()
        self.assertEqual(
            list(WarehouseProductItem.objects.values_list("pk", flat=True)), before)
        self.assertEqual(
            {wp.pk: wp.quantity for wp in WarehouseProduct.objects.all()},
            quantities)
        self.assertIn("already held", out)

    def test_undo_takes_the_stock_back_out(self):
        self._apply()
        self.assertTrue(WarehouseProductItem.objects.exists())
        self._run("--undo", "--apply")
        self.assertFalse(WarehouseProductItem.objects.exists())
        self.assertFalse(StockMovement.objects.filter(
            reference="READYMADE-STOCK-IMPORT").exists())

    def test_one_movement_per_product_records_the_intake(self):
        self._apply()
        movements = StockMovement.objects.filter(
            reference="READYMADE-STOCK-IMPORT")
        self.assertEqual(movements.count(), WarehouseProduct.objects.count())
        self.assertEqual(
            sum(m.quantity for m in movements),
            sum(i.quantity for i in WarehouseProductItem.objects.all()))


class TheUnplaceableRowsAreWrittenOnTheWarehouse(TestCase):
    """39 real sets sit in real boxes that the sheet cannot place, because
    the length column was smudged. Guessing would put stock on the shelf
    that is not there; a terminal report is something nobody reads twice.
    So they go on the warehouse's own page, where whoever can open the box
    will see them."""

    @classmethod
    def setUpTestData(cls):
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        Book.objects.create(name="Ergene Fabric", base_currency=usd)
        category = ProductCategory.objects.create(name="ready-made_curtain")
        peony = Product.objects.create(
            title="Peony", sku="RN1357", category=category)
        ProductVariant.objects.create(product=peony, variant_sku="RN1357.RM8")

    def setUp(self):
        self._dir = TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.spec = Path(self._dir.name) / "spec.xlsx"
        self.stock = Path(self._dir.name) / "stock.xlsx"
        _write_spec(self.spec)
        _write_stock(self.stock)

    def _apply(self):
        out = StringIO()
        call_command("import_readymade_stock", "--stock", str(self.stock),
                     "--spec", str(self.spec), "--apply", stdout=out, stderr=out)
        return out.getvalue()

    def _note(self):
        return Warehouse.objects.get(name="Ready-made Shop").description

    def test_the_note_names_the_box_and_the_count(self):
        self._apply()
        note = self._note()
        self.assertIn("BOXES THAT NEED A RECOUNT", note)
        self.assertIn("Box 16", note)
        self.assertIn("3 sets", note)

    def test_the_note_says_why_they_were_left_out(self):
        self._apply()
        self.assertIn("length column could not be read", self._note())

    def test_running_twice_does_not_stack_two_copies_of_it(self):
        self._apply()
        self._apply()
        self.assertEqual(self._note().count("BOXES THAT NEED A RECOUNT"), 1)

    def test_it_does_not_eat_anything_typed_above_it(self):
        """The description is an editable field. Whatever a person wrote in
        it has to survive the next import."""
        self._apply()
        wh = Warehouse.objects.get(name="Ready-made Shop")
        wh.description = "Shelf 3, back wall.\n\n" + wh.description
        wh.save(update_fields=["description"])
        self._apply()
        note = self._note()
        self.assertIn("Shelf 3, back wall.", note)
        self.assertEqual(note.count("BOXES THAT NEED A RECOUNT"), 1)
