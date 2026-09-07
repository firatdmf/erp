"""
Import the Ergene factory's fabric stock from the two workbooks the factory
system exports:

  FACTORY_GOODS.xlsx                     one row per physical TOP (kupon)
  Factory Stock Price <date> STOK.xlsx   one row per PATTERN (desen), priced

The goods file is the physical truth — 4,641 stock_items, ~100,888 metres — and the
price file is the money. They agree: 800 of the 840 patterns appear in both,
and for 785 of those the stock item count and metre total match to the decimal. So
metres come from the goods file only, and the price file is read for FIYAT
alone; where the two disagree on quantity, the shelf wins.

Two things about the goods export are worth knowing before reading the code.

It has no header row worth the name — the columns are literally "Column1",
"Column2", ... — so the positions below were established by profiling the
data, and are named here so nothing downstream has to count commas.

And its Turkish is damaged. Every cp1254 Turkish byte was glued to the byte
AFTER it and read back as one UTF-8 two-byte sequence, so "TEKSTIL" arrives
as "TEKST݌" and the pattern code "K24018INCI.G47" as "K24018ݎCݮG47".
`repair()` undoes it; the price file, which is clean, is what proved the
repair correct — it cut the unmatched patterns from 40 down to 29, and those
29 are genuinely absent from the price list rather than misspelled.

Idempotent. Products match on SKU, stock items on their printed barcode — or on
the factory's roll id for the two rows that carry no barcode. So a re-run of
the same files changes nothing, and a re-run of a NEWER export adds what is
new and re-states quantities and prices.

Dry run by default; pass --apply to commit. --undo takes it back out.

    python manage.py import_ergene_stock --apply
    python manage.py import_ergene_stock --undo --apply
"""
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from operating.models import (StockMovement, Warehouse, WarehouseProduct,
                              WarehouseProductItem)

DEFAULT_WAREHOUSE = "Ergene Factory"
DEFAULT_GOODS = Path.home() / "Desktop" / "FACTORY_GOODS.xlsx"
DEFAULT_PRICES = Path.home() / "Desktop" / "Factory Stock Price 16.07.2026 STOK.xlsx"

# Zero-based positions in the goods sheet. See the module docstring on why
# these are hardcoded rather than looked up by header.
C_ROLL_ID = 1      # the factory's own id for this stock item
C_DESEN = 3        # pattern code — the SKU, and the join to the price file
C_QUALITY = 4      # fabric type: GREK TUL, KARE SANAL, ...
C_COLOUR = 5       # colour: 317 KREM, 1395 BEYAZ, ...
C_METRES = 7       # metres on this stock item
C_GRADE = 11       # 1K first quality, 1A / 2K seconds
C_DESC = 15        # composition: "630 BEYAZ POLYESTER+KROSE"
C_LOCATION = 20    # MAMUL DEPO / RE-SEVKE HAZIR DEPO
C_BARCODE = 78     # the barcode printed on the stock item's label

# Everything not graded 1K is a factory second. Only 44 of 4,641 stock items.
FIRST_QUALITY = "1K"

# The price file's FIYAT is dollars per metre — it runs 1.70-17.00, the same
# scale the Laleli Fabrika warehouse prices in USD, and a fiftieth of what
# the figures would have to be to read as lira.
PRICE_CURRENCY = "USD"

# Tags every movement this command writes, so a run can be traced or undone.
IMPORT_REFERENCE = "ERGENE-STOCK-IMPORT"

# Prefix for barcodes we issue ourselves, kept visibly apart from the
# factory's own 13-digit "2000..." EAN-13s.
HOUSE_BARCODE_PREFIX = "X0"

# cp1254's Turkish letters, by the byte they occupy — the lead byte of each
# mangled pair identifies which letter was swallowed.
CP1254_TURKISH = {0xDD: "İ", 0xDE: "Ş", 0xD0: "Ğ",
                  0xF0: "ğ", 0xFD: "ı", 0xFE: "ş",
                  0xDC: "Ü", 0xD6: "Ö", 0xC7: "Ç"}


def repair(value):
    """Undo the goods export's mangling of Turkish text.

    A cp1254 Turkish byte was glued to the byte after it and the pair read
    as one UTF-8 two-byte sequence, which drops the second byte's stock item two
    bits. Those bits are gone, so the second character is recovered by what
    the remaining six can only have been: 0x20-0x3F is punctuation, a digit
    or a space and stands as itself; 0x1D and 0x1E are another Turkish
    letter; anything lower is an uppercase letter (six bits plus 0x40).

    Trailing HTML also leaks out of the source system ("A.GRI</TD>"), so
    cut at the first tag.
    """
    if not isinstance(value, str):
        return value
    out = []
    for ch in value:
        code = ord(ch)
        lead = 0xC0 | (code >> 6)
        if 0x0080 <= code <= 0x07FF and lead in CP1254_TURKISH:
            out.append(CP1254_TURKISH[lead])
            tail = code & 0x3F
            if tail >= 0x20:
                out.append(chr(tail))
            elif tail == 0x1D:
                out.append("İ")
            elif tail == 0x1E:
                out.append("Ş")
            else:
                out.append(chr(tail + 0x40))
        else:
            out.append(ch)
    return "".join(out).split("<")[0].strip()


def text(value):
    """A cleaned-up cell, or "" — the export writes everything as a string,
    including the literal "None" that str() leaves behind on empty cells."""
    if value is None:
        return ""
    s = repair(str(value)).strip()
    return "" if s in ("None", "-") else s


def stock_key(barcode, lot):
    """What identifies one physical stock item, for matching it against what the
    warehouse already holds.

    The printed barcode, normally — 4,639 of the 4,641 stock items carry a unique
    13-digit one. Two rows have no barcode at all, so those fall back to the
    factory's own roll id, which is unique across the whole file. Prefixed,
    so a roll id can never be mistaken for a barcode.

    Returns None when a stock item has neither, which no row currently does — such
    a stock item cannot be recognised on a later run and is always taken as new.
    """
    if barcode:
        return barcode
    if lot:
        return f"lot:{lot}"
    return None


def decimal(value):
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, AttributeError, ValueError):
        return None


def read_prices(path):
    """{DESEN: price per metre}. Header row DESEN/KUPON/METRE/FIYAT/TUTAR."""
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        prices = {}
        for row in wb.active.iter_rows(values_only=True):
            if not row:
                continue
            desen = text(row[0]).upper()
            if not desen or desen == "DESEN":
                continue
            price = decimal(row[3])
            if price is not None and price > 0:
                prices[desen] = price
        return prices
    finally:
        wb.close()


def read_stock(path):
    """Stock items grouped by pattern: {DESEN: {"name": ..., "tops": [...]}}.

    The per-pattern attributes are read off the FIRST stock item of that pattern —
    checked across the whole file, quality, colour and description never
    vary within a pattern; only the stock item number does.
    """
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb.active
        patterns = {}
        skipped = []
        for n, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if len(row) <= C_BARCODE:
                skipped.append(n)
                continue
            desen = text(row[C_DESEN]).upper()
            metres = decimal(row[C_METRES])
            if not desen or metres is None or metres <= 0:
                skipped.append(n)
                continue
            entry = patterns.get(desen)
            if entry is None:
                head = " ".join(b for b in (text(row[C_QUALITY]),
                                            text(row[C_COLOUR])) if b)
                desc = text(row[C_DESC])
                name = f"{head} · {desc}" if head and desc else (head or desc)
                entry = patterns[desen] = {"name": (name or desen)[:255],
                                           "tops": []}
            entry["tops"].append({
                "barcode": text(row[C_BARCODE]) or None,
                "metres": metres,
                "lot": text(row[C_ROLL_ID]) or None,
                "second": text(row[C_GRADE]).upper() != FIRST_QUALITY,
                "location": text(row[C_LOCATION]) or None,
            })
        return patterns, skipped
    finally:
        wb.close()


class _DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""


class Command(BaseCommand):
    help = "Import Ergene factory fabric stock from the goods + price workbooks."

    def add_arguments(self, parser):
        parser.add_argument("--goods", default=str(DEFAULT_GOODS))
        parser.add_argument("--prices", default=str(DEFAULT_PRICES))
        parser.add_argument("--warehouse", default=DEFAULT_WAREHOUSE)
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it the run is rolled back.")
        parser.add_argument("--undo", action="store_true",
                            help="Take the import back out: remove the stock items "
                                 "whose barcodes are in the goods file, and "
                                 "the products left holding none.")

    def handle(self, *args, **opts):
        goods_path, price_path = Path(opts["goods"]), Path(opts["prices"])
        for p in (goods_path, price_path):
            if not p.exists():
                raise CommandError(f"No such file: {p}")
        try:
            warehouse = Warehouse.objects.get(name=opts["warehouse"])
        except Warehouse.DoesNotExist:
            raise CommandError(f"No warehouse named {opts['warehouse']!r}")
        if warehouse.is_combined:
            raise CommandError(f"{warehouse} is a combined (ortak) warehouse "
                               "and holds no stock of its own.")

        prices = read_prices(price_path)
        patterns, skipped = read_stock(goods_path)
        stock_count = sum(len(p["tops"]) for p in patterns.values())
        self.stdout.write(f"{len(patterns)} patterns, {stock_count} stock items "
                          f"in {goods_path.name}")
        self.stdout.write(f"{len(prices)} priced patterns in {price_path.name}")
        if skipped:
            self.stdout.write(self.style.WARNING(
                f"{len(skipped)} goods rows had no pattern or no metres and were "
                f"skipped (rows {skipped[:10]}{'...' if len(skipped) > 10 else ''})"))

        usd_try = WarehouseProduct._usd_try_rate()
        if usd_try:
            self.stdout.write(f"USD/TRY {usd_try}")
        else:
            self.stdout.write(self.style.WARNING(
                "No USD/TRY rate available — cost_try left unset."))

        stats = None
        run = self._undo if opts["undo"] else self._import
        report = self._report_undo if opts["undo"] else self._report
        try:
            with transaction.atomic():
                stats = run(warehouse, patterns, prices, usd_try)
                if not opts["apply"]:
                    raise _DryRun
        except _DryRun:
            report(stats, applied=False)
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN — nothing was written. Re-run with --apply."))
            return
        report(stats, applied=True)

    def _undo(self, warehouse, patterns, prices, usd_try):
        """Take an import back out, using the goods file as the record of
        what it put in — a stock item is identified the same way the import matched
        it (see `stock_key`), so this removes what the file describes and
        nothing else.

        Stock items that have since been consumed or partly used are LEFT ALONE:
        they record real metres leaving the building, and deleting them
        would erase that. Same for a product still holding other stock —
        only ones the import left holding nothing at all are removed.
        """
        stock_items = [t for e in patterns.values() for t in e["tops"]]
        barcodes = {t["barcode"] for t in stock_items if t["barcode"]}
        lots = {t["lot"] for t in stock_items if not t["barcode"] and t["lot"]}
        described = Q(barcode__in=barcodes)
        if lots:
            # Matched on the factory's roll id alone, WITHOUT also requiring
            # the barcode to still be empty: an unlabelled stock item gets a house
            # barcode minted at import, so insisting on a blank one here
            # would strand exactly the stock items this branch exists to catch.
            described |= Q(lot_number__in=lots)
        mine = WarehouseProductItem.objects.filter(
            Q(product__warehouse=warehouse) & described)
        # Untouched since the import: still whole, still in stock.
        rolls = mine.filter(status="in_stock", meters_remaining=F("meters"))
        touched = set(rolls.values_list("product_id", flat=True))
        removed_stock = rolls.count()
        kept = mine.count() - removed_stock
        rolls.delete()
        StockMovement.objects.filter(product__warehouse=warehouse,
                                     reference=IMPORT_REFERENCE).delete()

        emptied = (WarehouseProduct.objects
                   .filter(pk__in=touched, stock_items__isnull=True)
                   .exclude(reservations__consumed=False))
        removed_products = emptied.count()
        emptied.delete()

        restated = 0
        for product in WarehouseProduct.objects.filter(pk__in=touched):
            total = sum(
                (r.meters_remaining if r.meters_remaining is not None
                 else r.meters)
                for r in product.stock_items.exclude(status="consumed")
            ) or Decimal("0")
            if product.quantity != total:
                product.quantity = total
                product.save(update_fields=["quantity", "updated_at"])
                restated += 1
        return {"tops": removed_stock, "kept": kept,
                "products": removed_products, "restated": restated}

    def _report_undo(self, s, applied):
        w = self.stdout.write
        w("")
        w(f"  stock items removed      {s['tops']:>7}")
        w(f"  stock items kept (used)  {s['kept']:>7}")
        w(f"  products removed  {s['products']:>7}")
        w(f"  products restated {s['restated']:>7}")
        if s["kept"]:
            w(self.style.WARNING(
                "  Stock items that were partly or fully used are left in place — "
                "they record metres that really left the warehouse."))

    def _import(self, warehouse, patterns, prices, usd_try):
        stats = {"products_created": 0, "products_updated": 0,
                 "stock_created": 0, "stock_existing": 0, "unpriced": [],
                 "barcodes_minted": 0,
                 "metres": Decimal("0"), "value_usd": Decimal("0")}

        # House codes for stock items the factory shipped without a printed label.
        # The warehouse's own minter, so an imported code can never collide
        # with one issued at the counter.
        from operating.views_warehouse import _barcode_minter
        mint_barcode = _barcode_minter(HOUSE_BARCODE_PREFIX)

        # Read the warehouse's whole current state up front and write it back
        # in bulk. Per-pattern queries would be ~3,400 round trips against a
        # remote database for the 840 patterns in the file, which took longer
        # than reading both workbooks by two orders of magnitude.
        existing = {p.sku.upper(): p for p in
                    WarehouseProduct.objects.filter(warehouse=warehouse)
                    .exclude(sku__isnull=True).exclude(sku="")}

        # Identity of every stock item already on these shelves, so a re-run — or an
        # overlap with stock items scanned in by hand — adds nothing twice. Live
        # metres per product come along for the ride: a merged product may
        # already hold stock items the file knows nothing about, and they still
        # count as stock.
        #
        # BOTH keys are recorded for each stock item, not just the one `stock_key`
        # would pick. A stock item that arrived unlabelled is matched by the
        # factory's roll id, but once we mint it a house barcode `stock_key`
        # starts answering with that barcode instead — and the file, which
        # still has no barcode for it, would stop matching and import it a
        # second time on the next run.
        seen = set()
        held = {}
        for pid, barcode, lot, meters, remaining in (
                WarehouseProductItem.objects
                .filter(product__warehouse=warehouse)
                .exclude(status="consumed")
                .values_list("product_id", "barcode", "lot_number", "meters",
                             "meters_remaining")):
            if barcode:
                seen.add(barcode)
            if lot:
                seen.add(f"lot:{lot}")
            held[pid] = held.get(pid, Decimal("0")) + (
                remaining if remaining is not None else meters)

        to_create, to_update, rolls, movements = [], [], [], []
        quantities = {}   # desen -> metres, resolved once every product has a pk

        for desen in sorted(patterns):
            entry = patterns[desen]
            price = prices.get(desen)
            if price is None:
                stats["unpriced"].append(desen)

            product = existing.get(desen)
            if product is None:
                product = WarehouseProduct(warehouse=warehouse, sku=desen,
                                           quantity=Decimal("0"))
                stats["products_created"] += 1
                to_create.append(product)
            else:
                stats["products_updated"] += 1
                to_update.append(product)
            product.name = entry["name"]
            if price is not None:
                product.purchase_price = price
                product.purchase_currency = PRICE_CURRENCY
                product.cost_usd = price
                product.cost_try = ((price * usd_try).quantize(Decimal("0.0001"))
                                    if usd_try else None)

            fresh = []
            for item in entry["tops"]:
                barcode = item["barcode"]
                key = stock_key(barcode, item["lot"])
                if key is not None and key in seen:
                    stats["stock_existing"] += 1
                    continue
                seen.add(key)
                notes = [item["location"], "2. kalite" if item["second"] else None]
                if not barcode:
                    # The factory sometimes ships a stock item with no printed label,
                    # and the goods file leaves the column empty. Every stock item
                    # must still be scannable, so mint a house code in the
                    # same X0 series the warehouse uses, and say on the roll
                    # why it does not carry a factory barcode.
                    barcode = mint_barcode()
                    stats["barcodes_minted"] += 1
                    notes.append(f"Fabrikadan barkodsuz geldi; {barcode} basıldı")
                fresh.append(WarehouseProductItem(
                    product=product, meters=item["metres"],
                    meters_remaining=item["metres"], barcode=barcode,
                    lot_number=item["lot"], status="in_stock",
                    is_second=item["second"],
                    notes=" · ".join(x for x in notes if x) or None,
                ))
            rolls.extend(fresh)
            stats["stock_created"] += len(fresh)
            if fresh:
                movements.append((product, sum(r.meters for r in fresh)))

            # Quantity is restated from the stock items on the shelf rather than
            # incremented, so a partial or repeated run cannot double it.
            total = (held.get(product.pk, Decimal("0"))
                     + sum(r.meters for r in fresh))
            quantities[desen] = product.quantity = total
            stats["metres"] += total
            if price is not None:
                stats["value_usd"] += total * price

        now = timezone.now()
        for product in to_update:
            # bulk_update does not run pre_save, so auto_now never fires and
            # the rows would keep the timestamp of whatever last touched them
            # — which the warehouse page's "recently updated" sort reads.
            product.updated_at = now
        WarehouseProduct.objects.bulk_create(to_create, batch_size=500)
        WarehouseProduct.objects.bulk_update(
            to_update,
            ["name", "quantity", "purchase_price", "purchase_currency",
             "cost_usd", "cost_try", "updated_at"], batch_size=500)
        # bulk_create assigns the pks the new rolls' FK needs, so the rolls
        # are built above but only written once every product exists.
        for roll in rolls:
            roll.product_id = roll.product.pk
        WarehouseProductItem.objects.bulk_create(rolls, batch_size=1000)
        StockMovement.objects.bulk_create([
            StockMovement(product_id=p.pk, movement_type="in", quantity=q,
                          reason="Ergene factory stock import",
                          reference=IMPORT_REFERENCE)
            for p, q in movements], batch_size=500)
        return stats

    def _report(self, s, applied):
        w = self.stdout.write
        w("")
        w(f"  products created  {s['products_created']:>7}")
        w(f"  products updated  {s['products_updated']:>7}")
        w(f"  stock items created      {s['stock_created']:>7}")
        if s["barcodes_minted"]:
            w(f"  barcodes minted   {s['barcodes_minted']:>7}  "
              f"(stock_items that arrived with no factory label)")
        w(f"  stock items already held {s['stock_existing']:>7}")
        w(f"  metres in stock   {s['metres']:>12,.2f}")
        w(f"  stock value       {s['value_usd']:>12,.2f} USD")
        if s["unpriced"]:
            w(self.style.WARNING(
                f"  {len(s['unpriced'])} patterns are not in the price list and "
                f"were imported unpriced:"))
            w("    " + ", ".join(s["unpriced"]))
        if applied:
            w(self.style.SUCCESS("\nImported. This run's stock items are traceable via:"))
            w(f'  StockMovement.objects.filter(reference="{IMPORT_REFERENCE}")')
