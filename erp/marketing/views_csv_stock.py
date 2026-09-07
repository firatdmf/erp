"""
CSV / Excel stock COMPARISON view.

Uploads a CSV or XLS/XLSX sheet and reports where its quantities disagree
with what the warehouse actually holds. Required columns: Kodu (SKU),
Miktar (Quantity).

It used to write those figures into Product.quantity /
ProductVariant.variant_quantity. Those columns are gone — catalog stock is
the sum of the WarehouseProduct rows behind a variant — so a sheet can no
longer overwrite the shelf. What it is still good for is exactly this:
telling you which lines disagree, so someone can go and count.
"""

import csv
import io
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from .models import Product, ProductVariant, with_live_quantity


def parse_decimal_smart(value):
    """
    Auto-detect decimal format and parse correctly.

    US/English format:  "2,146.40" (comma=thousands, dot=decimal)
    Turkish format:     "2.146,40" (dot=thousands, comma=decimal)
    Plain:              "513" or "513.8" or "513,8"
    """
    if not value:
        return Decimal('0')

    value = str(value).strip().strip('"')

    # Remove spaces and currency symbols
    value = value.replace(' ', '').replace('₺', '').replace('$', '').replace('€', '')

    if not value:
        return Decimal('0')

    has_comma = ',' in value
    has_dot = '.' in value

    if has_comma and has_dot:
        # Both present - whichever comes LAST is the decimal separator
        last_comma = value.rfind(',')
        last_dot = value.rfind('.')
        if last_dot > last_comma:
            # US format: "2,146.40" → remove commas, keep dot
            value = value.replace(',', '')
        else:
            # Turkish format: "2.146,40" → remove dots, comma→dot
            value = value.replace('.', '').replace(',', '.')
    elif has_comma:
        # Only comma: Turkish decimal "513,80" → "513.80"
        # But "1,234" could be US thousands - check digits after comma
        parts = value.split(',')
        if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
            # Likely US thousands: "1,234" → 1234
            value = value.replace(',', '')
        else:
            # Turkish decimal: "513,80" → "513.80"
            value = value.replace(',', '.')
    # else: only dot or no separator - already valid

    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal('0')


def parse_quantity(value):
    """
    Parse quantity from either numeric (Excel) or string (CSV) value.
    Excel returns float/int directly, CSV returns Turkish-formatted strings.
    """
    if value is None:
        return Decimal('0')

    # Already a number (from Excel) - use directly
    if isinstance(value, (int, float)):
        # Round to 2 decimal places to match DB field
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # String value (from CSV) - auto-detect format
    result = parse_decimal_smart(value)
    return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def extract_rows_from_csv(file_obj):
    """Parse CSV file and return list of dicts"""
    raw_content = file_obj.read()

    file_content = None
    for encoding in ['utf-8-sig', 'utf-8', 'cp1254', 'latin-1', 'cp1252', 'iso-8859-9']:
        try:
            file_content = raw_content.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if file_content is None:
        raise ValueError('Could not decode file. Please save as UTF-8 and try again.')

    # DEBUG: Print first 3 raw lines to see exact format
    raw_lines = file_content.split('\n')[:3]
    for i, line in enumerate(raw_lines):
        print(f"[CSV RAW LINE {i}]: {repr(line[:200])}")

    dialect = csv.Sniffer().sniff(file_content[:2048], delimiters=';,\t')
    print(f"[CSV] Detected delimiter: {repr(dialect.delimiter)}")
    reader = csv.DictReader(io.StringIO(file_content), delimiter=dialect.delimiter)
    rows = list(reader)
    if rows:
        print(f"[CSV] First parsed row: {rows[0]}")
    return rows


def extract_rows_from_excel(file_obj):
    """Parse XLS/XLSX file and return list of dicts, preserving numeric types"""
    import openpyxl

    wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [str(h).strip() if h else '' for h in rows[0]]
    result = []
    for row in rows[1:]:
        row_dict = {}
        for i, cell in enumerate(row):
            if i < len(headers):
                row_dict[headers[i]] = cell
        result.append(row_dict)

    wb.close()
    return result


def extract_data(rows):
    """Extract SKU → quantity mapping from parsed rows"""
    csv_data = {}
    total_rows = 0

    if rows:
        print(f"[IMPORT] Column headers: {list(rows[0].keys())}")
        print(f"[IMPORT] First row sample: {rows[0]}")

    for row in rows:
        total_rows += 1
        code = None
        quantity = None

        for key, value in row.items():
            if key is None:
                continue
            key_lower = str(key).lower().strip()

            if key_lower in ['kodu', 'kod', 'code', 'sku', 'stok kodu', 'ürün kodu', 'urun kodu']:
                code = str(value).strip() if value else None
            elif key_lower in ['miktar', 'quantity', 'stok', 'adet', 'rezerv sonrası mikta', 'rezerv sonrasi mikta']:
                quantity = parse_quantity(value)

        if code and quantity is not None:
            csv_data[code] = quantity

    print(f"[IMPORT] Extracted {len(csv_data)} SKU codes from {total_rows} rows")
    if csv_data:
        sample = list(csv_data.items())[:5]
        print(f"[IMPORT] Sample data: {sample}")

    return csv_data, total_rows


@login_required
@require_POST
@csrf_protect
def csv_stock_update(request):
    """
    Process uploaded CSV/XLS/XLSX and update Product + ProductVariant quantities.
    Searches BOTH Product.sku and ProductVariant.variant_sku.
    """
    if 'csv_file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)

    uploaded_file = request.FILES['csv_file']
    filename = uploaded_file.name.lower()

    try:
        if filename.endswith('.csv'):
            rows = extract_rows_from_csv(uploaded_file)
        elif filename.endswith(('.xls', '.xlsx')):
            rows = extract_rows_from_excel(uploaded_file)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Unsupported file format. Please upload CSV, XLS, or XLSX.'
            }, status=400)

        csv_data, total_rows = extract_data(rows)

        if not csv_data:
            return JsonResponse({
                'success': False,
                'error': 'No valid data found. Required columns: "Kodu" and "Miktar"'
            }, status=400)

        matched_count = 0
        differing_count = 0
        not_found = []
        differences = []
        matched_codes = set()

        def _diff(sku, name, kind, sheet_qty, live_qty, tracked):
            """A line is only a disagreement if the warehouse has an opinion.
            An untracked SKU (no warehouse row at all) is reported apart —
            the sheet is not wrong about it, we simply hold none of it."""
            return {
                'sku': sku, 'name': name, 'type': kind,
                'sheet': str(sheet_qty),
                'warehouse': str(live_qty) if live_qty is not None else None,
                'stock_tracked': tracked,
                'difference': (str(sheet_qty - live_qty)
                               if live_qty is not None else None),
            }

        # 1) Match against ProductVariant.variant_sku
        variants = with_live_quantity(
            ProductVariant.objects.filter(variant_sku__in=csv_data.keys())
        ).select_related('product')

        for variant in variants:
            code = variant.variant_sku
            sheet_qty = csv_data[code]
            matched_codes.add(code)
            matched_count += 1

            live = variant.live_quantity
            if live is None or live != sheet_qty:
                differing_count += 1
                differences.append(_diff(
                    code, f"{variant.product.title} / {code}", 'variant',
                    sheet_qty, live, variant.stock_tracked))

        # 2) Match remaining codes against Product.sku
        remaining_codes = set(csv_data.keys()) - matched_codes
        if remaining_codes:
            products = Product.objects.filter(sku__in=remaining_codes)
            for product in products:
                sheet_qty = csv_data[product.sku]
                matched_codes.add(product.sku)
                matched_count += 1

                live = product.live_quantity
                if live is None or live != sheet_qty:
                    differing_count += 1
                    differences.append(_diff(
                        product.sku, product.title, 'product',
                        sheet_qty, live, live is not None))

        # 3) Codes not found in either
        not_found = [code for code in csv_data.keys() if code not in matched_codes]

        print(f"[COMPARE] Matched: {matched_count}, Differing: {differing_count}, "
              f"Not found: {len(not_found)}")

        return JsonResponse({
            'success': True,
            'read_only': True,
            'total_rows': total_rows,
            'matched': matched_count,
            'differing': differing_count,
            'not_found_count': len(not_found),
            'not_found': not_found[:20],
            'differences': differences[:50],
            'message': (f'{differing_count} of {matched_count} matched line(s) '
                        f'disagree with the warehouse. Nothing was changed.'),
        })

    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except csv.Error as e:
        return JsonResponse({'success': False, 'error': f'File parse error: {str(e)}'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'}, status=500)
