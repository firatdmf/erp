"""
The price round-trip for a factory warehouse: send out what has no price,
read back what the factory quotes.

    python manage.py ergene_prices --export ~/Desktop/unpriced.xlsx
    python manage.py ergene_prices --import ~/Desktop/unpriced.xlsx --apply

The exported sheet is laid out like the factory's own "STOK" price list —
DESEN / KUPON / METRE / FIYAT / TUTAR, with FIYAT blank — so whatever comes
back reads the same way whether they filled in our sheet or sent a fresh
export of their own. Two extra columns after TUTAR carry the product name
and the stock items' barcodes, so a human can tell which fabric is being quoted;
the reader ignores them, and finds FIYAT by its header rather than its
position so the extra columns cannot shift it out from under itself.

Prices are per metre in USD, matching `import_ergene_stock`. A row with no
FIYAT is passed over rather than treated as zero — an unquoted pattern stays
unpriced instead of silently becoming free.

Dry run by default; pass --apply to commit.
"""
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from operating.models import Warehouse, WarehouseProduct

from .import_ergene_stock import (DEFAULT_WAREHOUSE, PRICE_CURRENCY, decimal,
                                  text)

# What the price column may be called. The factory writes FİYAT; a sheet
# that has been through a system with broken Turkish writes FIYAT or F?YAT.
PRICE_HEADERS = {"FIYAT", "FİYAT", "PRICE", "BIRIM FIYAT", "BİRİM FİYAT"}
SKU_HEADERS = {"DESEN", "SKU", "KOD", "STOK KODU"}


def _headers(row):
    return [text(c).upper() for c in row]


def _find_columns(row):
    """(sku column, price column) from a header row, or (None, None)."""
    heads = _headers(row)
    sku = price = None
    for i, h in enumerate(heads):
        if sku is None and h in SKU_HEADERS:
            sku = i
        if price is None and h in PRICE_HEADERS:
            price = i
    return sku, price


class _DryRun(Exception):
    """Raised at the end of a dry run to roll the transaction back."""


class Command(BaseCommand):
    help = "Export a factory warehouse's unpriced patterns, or read prices back in."

    def add_arguments(self, parser):
        parser.add_argument("--export", metavar="FILE",
                            help="Write the unpriced patterns to this .xlsx")
        parser.add_argument("--import", dest="import_file", metavar="FILE",
                            help="Read prices from this .xlsx")
        parser.add_argument("--warehouse", default=DEFAULT_WAREHOUSE)
        parser.add_argument("--apply", action="store_true",
                            help="Commit. Without it the run is rolled back.")

    def handle(self, *args, **opts):
        if bool(opts["export"]) == bool(opts["import_file"]):
            raise CommandError("Give exactly one of --export or --import.")
        try:
            warehouse = Warehouse.objects.get(name=opts["warehouse"])
        except Warehouse.DoesNotExist:
            raise CommandError(f"No warehouse named {opts['warehouse']!r}")

        if opts["export"]:
            return self._export(warehouse, Path(opts["export"]).expanduser())

        path = Path(opts["import_file"]).expanduser()
        if not path.exists():
            raise CommandError(f"No such file: {path}")
        try:
            with transaction.atomic():
                stats = self._read(warehouse, path)
                if not opts["apply"]:
                    raise _DryRun
        except _DryRun:
            self._report(stats)
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN — nothing was written. Re-run with --apply."))
            return
        self._report(stats)
        self.stdout.write(self.style.SUCCESS("\nPrices saved."))

    def _export(self, warehouse, path):
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        products = (WarehouseProduct.objects
                    .filter(warehouse=warehouse, purchase_price__isnull=True)
                    .prefetch_related("stock_items").order_by("-quantity"))
        wb = Workbook()
        ws = wb.active
        ws.title = "FIYAT BEKLEYEN"
        head = ["DESEN", "KUPON", "METRE", "FİYAT", "TUTAR", "ÜRÜN", "BARKOD"]
        ws.append(head)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="EEEEEE")
            cell.alignment = Alignment(horizontal="center")
        # FIYAT is the column they fill in, so it is the one tinted.
        fill_me = PatternFill("solid", fgColor="FFF6D5")

        rows = 0
        for p in products:
            stock_items = [r for r in p.stock_items.all() if r.status != "consumed"]
            ws.append([p.sku, len(stock_items), float(p.quantity or 0), None, None,
                       p.name,
                       ", ".join(r.barcode for r in stock_items if r.barcode)])
            rows += 1
            ws.cell(row=ws.max_row, column=4).fill = fill_me
            # Left as a formula, so a price typed in shows its own line total
            # and the sheet adds up for whoever is quoting it.
            ws.cell(row=ws.max_row, column=5).value = (
                f"=IF(D{ws.max_row}=\"\",\"\",C{ws.max_row}*D{ws.max_row})")

        for col, width in zip("ABCDEFG", (18, 8, 10, 10, 12, 58, 46)):
            ws.column_dimensions[col].width = width
        ws.freeze_panes = "A2"

        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            wb.save(path)
        except PermissionError:
            # Windows locks a workbook that is open in Excel, and openpyxl
            # surfaces that as a bare traceback three frames deep.
            raise CommandError(
                f"{path} is locked — it is most likely open in Excel. Close "
                f"it, or pass --export with a different filename.")
        self.stdout.write(self.style.SUCCESS(
            f"{rows} unpriced patterns written to {path}"))
        self.stdout.write("Send it out, then read the reply back with:")
        self.stdout.write(f"  python manage.py ergene_prices --import "
                          f"{path} --apply")

    def _read(self, warehouse, path):
        from openpyxl import load_workbook

        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb.active
            rows = ws.iter_rows(values_only=True)
            sku_col = price_col = None
            for row in rows:
                if row:
                    sku_col, price_col = _find_columns(row)
                    if sku_col is not None and price_col is not None:
                        break
            if sku_col is None or price_col is None:
                raise CommandError(
                    f"{path.name} has no header row naming both a pattern "
                    f"column ({'/'.join(sorted(SKU_HEADERS))}) and a price "
                    f"column ({'/'.join(sorted(PRICE_HEADERS))}).")
            quoted = {}
            for row in rows:
                if not row or len(row) <= max(sku_col, price_col):
                    continue
                sku = text(row[sku_col]).upper()
                price = decimal(row[price_col])
                # No price means not quoted yet — never a price of zero.
                if sku and price is not None and price > 0:
                    quoted[sku] = price
        finally:
            wb.close()

        usd_try = WarehouseProduct._usd_try_rate()
        by_sku = {p.sku.upper(): p for p in
                  WarehouseProduct.objects.filter(warehouse=warehouse)
                  .exclude(sku__isnull=True).exclude(sku="")}

        stats = {"quoted": len(quoted), "set": [], "changed": [],
                 "same": 0, "unknown": [], "rate": usd_try}
        now = timezone.now()
        to_save = []
        for sku, price in quoted.items():
            product = by_sku.get(sku)
            if product is None:
                stats["unknown"].append(sku)
                continue
            was = product.purchase_price
            if was == price and (product.purchase_currency or "") == PRICE_CURRENCY:
                stats["same"] += 1
                continue
            # The old currency travels with the old figure: a product can
            # be "changed" purely by moving to USD at the same number, and
            # a bare "4.40 -> 4.40" would read as a no-op.
            was_cur = (product.purchase_currency or "").upper()
            (stats["set"] if was is None else stats["changed"]).append(
                (sku, was, was_cur, price, product.quantity))
            product.purchase_price = price
            product.purchase_currency = PRICE_CURRENCY
            product.cost_usd = price
            product.cost_try = ((price * usd_try).quantize(Decimal("0.0001"))
                                if usd_try else None)
            product.updated_at = now
            to_save.append(product)

        WarehouseProduct.objects.bulk_update(
            to_save, ["purchase_price", "purchase_currency", "cost_usd",
                      "cost_try", "updated_at"], batch_size=500)
        stats["still_unpriced"] = (
            WarehouseProduct.objects
            .filter(warehouse=warehouse, purchase_price__isnull=True).count())
        return stats

    def _report(self, s):
        w = self.stdout.write
        w("")
        w(f"  prices in the file  {s['quoted']:>6}")
        w(f"  newly priced        {len(s['set']):>6}")
        w(f"  price changed       {len(s['changed']):>6}")
        w(f"  already matching    {s['same']:>6}")
        w(f"  still unpriced      {s['still_unpriced']:>6}")
        if s["set"]:
            w("\n  newly priced:")
            for sku, _was, _cur, now, qty in sorted(s["set"]):
                w(f"    {sku:18} {now:>7} USD/m  x {qty} m")
        if s["changed"]:
            w(self.style.WARNING("\n  price CHANGED on patterns that already "
                                 "had one:"))
            for sku, was, cur, now, qty in sorted(s["changed"]):
                w(f"    {sku:18} {was} {cur or '?'} -> {now} {PRICE_CURRENCY}"
                  f"  per metre, x {qty} m")
        if s["unknown"]:
            w(self.style.WARNING(
                f"\n  {len(s['unknown'])} patterns in the file are not in this "
                f"warehouse and were ignored:"))
            w("    " + ", ".join(sorted(s["unknown"])[:40]))
