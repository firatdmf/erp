"""Put the ready-made curtain stock on a shelf.

2,835 sets in 179 boxes, counted by hand into
ready-made-curtains-stock.xlsx (sheet GÜNCEL) and worth $50,909.10 at the
prices the same sheet carries. None of it existed in any warehouse.

WHAT A ROW IS. One row is one BOX holding N sets of a single design /
length / colour / header. A box can hold several rows — box 100 holds seven
different combinations, box 237 holds nine — so the box is a place, not a
product. Where a row has no box number it belongs to the box above it, and
the reader carries that number down. There are 233 such rows and exactly
233 distinct (variant, box) pairs: no design repeats within one box, which
is what makes the pair a usable key for re-running this.

WHAT A STOCK ITEM IS. One per row: "20 sets of Peony 84in, in box 12".
Not one per set — 2,835 rows nobody labels individually — and not one per
box, because a box is not one product. The box number goes in
`lot_number`, so a picker is told which of the 11 boxes holding Leather
84in to open.

BARCODES. Identical curtain sets share one printed EAN, which is a
product-level fact, so it goes on WarehouseProduct.barcode (not unique).
WarehouseProductItem.barcode is UNIQUE and identifies one physical thing —
meaningful for a roll of fabric, where every roll is a different length,
and impossible for interchangeable sets. It is left null. Scanning still
works: warehouse_barcode_lookup falls back from stock item to product
barcode and answers with the SKU and its stock items.

MATCHING. The warehouse's colour words are unreliable — a Peony box marked
KREM is Mürdüm, because Mürdüm is the only Peony there is. So a row is
matched on (design, header, length), and the colour is consulted ONLY when
the Karven spec offers more than one colourway for those three. See
marketing/management/commands/fix_readymade_catalog.py, which made the
catalog agree with that same spec.

WHAT IS LEFT OUT. Rows whose length reads "*" — the tally was smudged and
nobody knows whether they are 84in or 95in. They are reported, not
guessed at, and want a recount on the floor.

Dry run by default; pass --apply to commit. --undo takes it back out.

    python manage.py import_readymade_stock
    python manage.py import_readymade_stock --apply
    python manage.py import_readymade_stock --undo --apply
"""
import collections
import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from marketing.models import Product, ProductVariant
from operating.models import (StockMovement, Warehouse, WarehouseProduct,
                              WarehouseProductItem)

DEFAULT_STOCK = Path.home() / "Desktop" / "ready-made-curtains-stock.xlsx"
DEFAULT_SPEC = Path.home() / "Desktop" / "KarvenReadyMadeStock.xlsx"

WAREHOUSE_NAME = "Ready-made Shop"
BOOK_NAME = "Ergene Fabric"

# Sold as packaged sets, one EAN per set — not by the metre. The sets
# then travel in cartons, which is what one stock item here is: the two
# are separate facts and the command states both rather than letting one
# be inferred from the other.
UNIT = "pack"
PACK_TYPE = "box"

# The sheet's prices run $12.40-$26.50 a set, the same scale as the Karven
# spec's own price column, which is dollars.
PRICE_CURRENCY = "USD"

# Tags every row this command writes, so a run can be traced or undone.
IMPORT_REFERENCE = "READYMADE-STOCK-IMPORT"

# The rows this command cannot place get written into the warehouse's own
# description, which the detail page renders and the warehouse form lets
# anyone edit. A report that only exists in a terminal is a report nobody
# reads; this one is on the page next to the stock it is about.
#
# Everything from the marker down is rewritten on each run, so a recount
# that fixes the sheet shrinks the list instead of appending a second copy.
# Anything typed ABOVE the marker is left alone.
NOTE_MARKER = "── BOXES THAT NEED A RECOUNT ──"

# Markers this note has been written under before. The block is found by
# its heading, so renaming the heading orphans the old one — it stops
# matching and survives as "text the user typed", which is exactly what
# happened the first time this was translated. Every past heading has to
# stay listed here for the rewrite to find and replace its own work.
LEGACY_NOTE_MARKERS = ["── SAYIM GEREKEN KUTULAR ──"]

# The count sheet's colour words, for display. These rows have no length,
# so their Karven colourway cannot be resolved — the sheet's own word is
# all there is to go on.
COLOUR_EN = {
    "BEYAZ": "white",
    "KREM": "cream",
    "D BEYAZ": "off-white",
    "TURKUAZ": "turquoise",
}

# Sheet column positions in GÜNCEL (0-based), after the index column.
C_BOX, C_DESIGN, C_LENGTH, C_COLOUR, C_HEADER, C_SETS, C_PRICE = 1, 2, 3, 4, 5, 6, 7

# Sheet header word -> the letter the catalog uses.
HEADER_LETTER = {"CEPLİ": "R", "HALKALI": "G"}

# Sheet colour word -> the spec's own colourway name. Used ONLY to break a
# tie when a design offers two colourways for one header and length.
SHEET_COLOUR = {
    "BEYAZ": "Beyaz",
    "KREM": "Şampanya",
    "D BEYAZ": "Kirli Beyaz",
    "TURKUAZ": "Turkuaz",
}

# Rose (48060) is made in Beyaz and Kirli Beyaz only, but 35 sets of it are
# written up as KREM and two carry no colour at all. Kirli Beyaz is the
# nearer of the two to what "krem" describes, and the sheet already spells
# Kirli Beyaz as "D BEYAZ" elsewhere — so these are boxes where somebody
# reached for the softer word. Muhammed's call, recorded here rather than
# buried in a lookup.
COLOUR_OVERRIDES = {
    ("48060", "R", "KREM"): "Kirli Beyaz",
    ("48060", "R", "*"): "Kirli Beyaz",
    ("48060", "R", "None"): "Kirli Beyaz",
}

PARENT_RE = re.compile(r"^R[KN]?\d+$")


def digits(value):
    return "".join(c for c in str(value) if c.isdigit())


def decimal(value):
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except Exception:
        return None


def read_spec(path):
    """{(design, header, length): [(colourway, barcode, price), ...]}.

    The spec writes design codes inconsistently — RN1268, R12471, RK24539,
    RR1370 all appear for what are four ordinary designs — so only the
    digits are kept.
    """
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb.active
        spec = collections.defaultdict(list)
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0] or not isinstance(row[2], (int, float)):
                continue
            header = "G" if str(row[5]).strip().lower().startswith("grommet") else "R"
            spec[(digits(row[0]), header, int(row[2]))].append(
                (str(row[1]).strip(),
                 str(int(row[11])) if row[11] is not None else None,
                 decimal(row[10])))
        return dict(spec)
    finally:
        wb.close()


def read_stock(path):
    """The GÜNCEL sheet as rows, with box numbers carried down.

    Skips the TOTAL row and the two loose notes below the table ("86
    numaralı kutu nerde?"), which have no design code.
    """
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["GÜNCEL"]
        rows, box = [], None
        for n, raw in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not raw or raw[C_DESIGN] is None:
                continue
            if str(raw[C_BOX]).strip().upper() == "TOTAL":
                continue
            if isinstance(raw[C_BOX], (int, float)):
                box = int(raw[C_BOX])
            length = raw[C_LENGTH]
            rows.append({
                "line": n,
                "box": box,
                "design": digits(raw[C_DESIGN]),
                "length": int(length) if isinstance(length, (int, float)) else None,
                "colour": str(raw[C_COLOUR]).strip().upper(),
                "header": HEADER_LETTER.get(str(raw[C_HEADER]).strip()),
                "sets": decimal(raw[C_SETS]) or Decimal("0"),
                "price": decimal(raw[C_PRICE]),
            })
        return rows
    finally:
        wb.close()


class Command(BaseCommand):
    help = "Import the ready-made curtain stock into the Ready-made Shop."

    def add_arguments(self, parser):
        parser.add_argument("--stock", default=str(DEFAULT_STOCK))
        parser.add_argument("--spec", default=str(DEFAULT_SPEC))
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it the run is rolled back.")
        parser.add_argument("--undo", action="store_true",
                            help="Remove what a previous run created.")

    def handle(self, *args, **options):
        applied = options["apply"]
        stats = None
        try:
            with transaction.atomic():
                if options["undo"]:
                    stats = self._undo()
                else:
                    stock_path, spec_path = Path(options["stock"]), Path(options["spec"])
                    for p in (stock_path, spec_path):
                        if not p.exists():
                            raise CommandError(f"Not found: {p}")
                    stats = self._run(read_stock(stock_path), read_spec(spec_path))
                if not applied:
                    raise _Rollback()
        except _Rollback:
            pass
        (self._report_undo if options["undo"] else self._report)(stats, applied)

    # ------------------------------------------------------------------
    def _warehouse(self):
        """The shelf these goods stand on, created once.

        Ergene's book: stock belongs to whoever owns the shelves, and
        WarehouseProduct rows here will show up in that book's inventory on
        the balance sheet the moment they exist — accounting reads live
        stock items rather than waiting for a journal entry.
        """
        from accounting.models import Book

        book = Book.objects.filter(name=BOOK_NAME).first()
        if book is None:
            raise CommandError(f"No accounting book named {BOOK_NAME!r}")
        warehouse, created = Warehouse.objects.get_or_create(
            name=WAREHOUSE_NAME,
            defaults={"accounting_book": book, "kind": "normal",
                      "description": "Ready-made curtain stock"},
        )
        if not created and warehouse.accounting_book_id != book.pk:
            raise CommandError(
                f"{WAREHOUSE_NAME!r} already exists under a different book "
                f"({warehouse.accounting_book}). Refusing to move stock "
                f"between books.")
        return warehouse, created

    def _variants(self):
        """{(design, header letter, colour letter, length digit): variant}."""
        found = {}
        for p in Product.objects.filter(sku__istartswith="R"):
            if not PARENT_RE.match(p.sku or ""):
                continue
            for v in p.variants.all():
                bare = v.variant_sku.replace(".", "")
                suffix = bare[len(p.sku):].upper()
                if len(suffix) == 3:
                    found[(digits(p.sku), suffix[0], suffix[1], suffix[2])] = v
        return found

    def _resolve(self, row, spec, variants, colour_letters):
        """(variant, barcode, note) for a sheet row, or (None, None, why)."""
        if row["length"] is None:
            return None, None, "length unreadable in the sheet"
        if row["header"] is None:
            return None, None, "header type unreadable in the sheet"

        key = (row["design"], row["header"], row["length"])
        candidates = spec.get(key, [])
        if not candidates:
            return None, None, f"no Karven spec row for {key}"

        if len(candidates) == 1:
            # One colourway for this design/header/length, so the sheet's
            # colour word carries no information and is not consulted.
            colourway, barcode, _price = candidates[0]
        else:
            override = COLOUR_OVERRIDES.get(
                (row["design"], row["header"], row["colour"]))
            want = override or SHEET_COLOUR.get(row["colour"])
            match = [c for c in candidates if c[0] == want]
            if len(match) != 1:
                return None, None, (
                    f"colour {row['colour']!r} does not pick one of "
                    f"{[c[0] for c in candidates]}")
            colourway, barcode, _price = match[0]

        letter = colour_letters.get(colourway)
        if letter is None:
            return None, None, f"no letter for colourway {colourway!r}"
        variant = variants.get(
            (row["design"], row["header"], letter,
             "8" if row["length"] == 84 else "9"))
        if variant is None:
            return None, None, (
                f"no catalog variant for {row['design']} "
                f"{row['header']}{letter}{'8' if row['length'] == 84 else '9'} "
                f"({colourway})")
        return variant, barcode, None

    def _run(self, rows, spec):
        from marketing.management.commands.fix_readymade_catalog import COLOUR_LETTER

        warehouse, created_warehouse = self._warehouse()
        variants = self._variants()
        usd_try = WarehouseProduct._usd_try_rate()

        stats = {"warehouse_created": created_warehouse, "skipped": [],
                 "products": 0, "items": 0, "existing": 0,
                 "sets": Decimal("0"), "value": Decimal("0"),
                 "skipped_sets": Decimal("0")}

        # What this shelf already holds, so a re-run adds only what is new.
        # The key is (product, box) — 233 rows, 233 distinct pairs.
        held = {(i.product_id, i.lot_number)
                for i in WarehouseProductItem.objects.filter(
                    product__warehouse=warehouse)}

        by_product = collections.defaultdict(list)
        for row in rows:
            variant, barcode, why = self._resolve(
                row, spec, variants, COLOUR_LETTER)
            if variant is None:
                stats["skipped"].append((row, why))
                stats["skipped_sets"] += row["sets"]
                continue
            by_product[(variant, barcode)].append(row)

        for (variant, barcode), variant_rows in sorted(
                by_product.items(), key=lambda kv: kv[0][0].variant_sku):
            price = next((r["price"] for r in variant_rows if r["price"]), None)
            wp, made = WarehouseProduct.objects.get_or_create(
                warehouse=warehouse, sku=variant.variant_sku,
                defaults={
                    "name": variant.full_name or variant.variant_sku,
                    "quantity": Decimal("0"),
                    "unit": UNIT,
                    "pack_type": PACK_TYPE,
                },
            )
            stats["products"] += 1
            # Restated every run rather than only on create, so a corrected
            # price or a newly-linked variant lands on a re-import too.
            wp.barcode = barcode or wp.barcode
            wp.catalog_variant = variant
            wp.unit = UNIT
            wp.pack_type = PACK_TYPE
            if price:
                wp.purchase_price = price
                wp.purchase_currency = PRICE_CURRENCY
                wp.cost_usd = price
                wp.cost_try = ((price * usd_try).quantize(Decimal("0.0001"))
                               if usd_try else None)

            fresh = []
            for row in variant_rows:
                box = str(row["box"]) if row["box"] is not None else None
                if (wp.pk, box) in held:
                    stats["existing"] += 1
                    continue
                held.add((wp.pk, box))
                fresh.append(WarehouseProductItem(
                    product=wp,
                    quantity=row["sets"],
                    quantity_remaining=row["sets"],
                    # Left null on purpose: every set of one SKU carries the
                    # same printed EAN, which lives on the product. See the
                    # module docstring.
                    barcode=None,
                    lot_number=box,
                    status="in_stock",
                    unit_cost_base=row["price"],
                    notes=f"{IMPORT_REFERENCE} · sheet row {row['line']}"
                          + (f" · kutu {box}" if box else " · kutusuz"),
                ))
                stats["sets"] += row["sets"]
                if row["price"]:
                    stats["value"] += row["sets"] * row["price"]

            WarehouseProductItem.objects.bulk_create(fresh, batch_size=500)  # noqa: E501
            stats["items"] += len(fresh)

            # Quantity is restated from what stands on the shelf rather than
            # incremented, so a partial or repeated run cannot double it.
            wp.quantity = (WarehouseProductItem.objects
                           .filter(product=wp).exclude(status="consumed")
                           .aggregate(t=_sum_remaining())["t"] or Decimal("0"))
            wp.save()

            if fresh:
                StockMovement.objects.create(
                    product=wp, movement_type="in",
                    quantity=sum((f.quantity for f in fresh), Decimal("0")),
                    reason="Ready-made curtain stock intake",
                    reference=IMPORT_REFERENCE)

        self._write_recount_note(warehouse, stats["skipped"])
        return stats

    def _write_recount_note(self, warehouse, skipped):
        """Put the rows that could not be placed on the warehouse page.

        These are real sets sitting in real boxes — they are simply not
        countable from the sheet, because the length column was smudged.
        Guessing 84in or 95in would put stock on the shelf that is not
        there; leaving them only in a terminal report means nobody ever
        looks again. So they go where the person who can open the box
        will see them.
        """
        head = warehouse.description or ""
        for marker in [NOTE_MARKER, *LEGACY_NOTE_MARKERS]:
            head = head.split(marker)[0]
        head = head.rstrip()
        if not skipped:
            warehouse.description = head or None
            warehouse.save(update_fields=["description", "updated_at"])
            return

        by_box = collections.defaultdict(list)
        for row, _why in skipped:
            by_box[row["box"]].append(row)
        total = sum(r["sets"] for r, _ in skipped)

        lines = [
            head,
            "",
            NOTE_MARKER,
            f"{_sets(total)} across {len(skipped)} lines were NOT added "
            f"to stock.",
            "The length column could not be read on the count sheet — "
            "84in or 95in is unknown, and was not guessed at.",
            "Open the boxes, measure, then add them by hand.",
            "",
        ]
        for box in sorted(by_box, key=lambda b: (b is None, b)):
            rows = by_box[box]
            label = f"Box {box}" if box is not None else "No box number"
            lines.append(f"{label} — {_sets(sum(r['sets'] for r in rows))}")
            for r in rows:
                header = "rod pocket" if r["header"] == "R" else "grommet"
                colour = COLOUR_EN.get(r["colour"], r["colour"].lower())
                lines.append(
                    f"    design {r['design']} · {colour} · {header} · "
                    f"{_sets(r['sets'])}  (sheet row {r['line']})")
        warehouse.description = "\n".join(lines).strip()
        warehouse.save(update_fields=["description", "updated_at"])

    def _undo(self):
        warehouse = Warehouse.objects.filter(name=WAREHOUSE_NAME).first()
        if warehouse is None:
            return {"items": 0, "movements": 0, "products": 0}
        items = WarehouseProductItem.objects.filter(
            product__warehouse=warehouse, notes__startswith=IMPORT_REFERENCE)
        movements = StockMovement.objects.filter(
            product__warehouse=warehouse, reference=IMPORT_REFERENCE)
        counts = {"items": items.count(), "movements": movements.count()}
        items.delete()
        movements.delete()
        empty = (WarehouseProduct.objects.filter(warehouse=warehouse)
                 .exclude(stock_items__isnull=False))
        counts["products"] = empty.count()
        empty.delete()
        return counts

    # ------------------------------------------------------------------
    def _report(self, s, applied):
        w = self.stdout.write
        w("")
        if s["warehouse_created"]:
            w(self.style.SUCCESS(f"  created warehouse {WAREHOUSE_NAME!r} "
                                 f"under the {BOOK_NAME} book"))
        w(f"  products         {s['products']:>7}")
        w(f"  stock items      {s['items']:>7}")
        if s["existing"]:
            w(f"  already held     {s['existing']:>7}")
        w(f"  sets             {s['sets']:>7,.0f}")
        w(f"  value            {s['value']:>10,.2f} USD")
        if s["skipped"]:
            w("")
            w(self.style.WARNING(
                f"  {len(s['skipped'])} row(s), {s['skipped_sets']:,.0f} sets, "
                f"left on the floor for a recount:"))
            grouped = collections.Counter(why for _row, why in s["skipped"])
            for why, n in grouped.most_common():
                w(f"      {n:>3} row(s)  {why}")
            for row, why in s["skipped"][:40]:
                w(f"        row {row['line']:>3} kutu {str(row['box']):>4}  "
                  f"{row['design']} {row['length'] or '*'} {row['colour']} "
                  f"({row['sets']:.0f} sets)")
        w("")
        w(self.style.SUCCESS("Imported.") if applied else
          self.style.WARNING("Dry run — nothing written. Re-run with --apply."))

    def _report_undo(self, s, applied):
        w = self.stdout.write
        w(f"\n  stock items removed {s['items']:>7}")
        w(f"  movements removed   {s['movements']:>7}")
        w(f"  empty products      {s['products']:>7}")
        w(self.style.SUCCESS("\nRemoved.") if applied else
          self.style.WARNING("\nDry run — nothing removed."))


def _sets(n):
    """"1 set" / "20 sets" — the note is read by a person holding a box."""
    return f"{n:.0f} set" + ("" if n == 1 else "s")


def _sum_remaining():
    from django.db.models import Sum
    return Sum("quantity_remaining")


class _Rollback(Exception):
    """Unwinds the transaction at the end of a dry run."""
