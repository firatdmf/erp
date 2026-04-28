"""Warehouse views — list, detail, create, import products from Excel."""
import json
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, F, DecimalField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from .models import Warehouse, WarehouseProduct


def _safe_decimal(value, default=None):
    """Convert any cell value to Decimal, returning default on failure."""
    if value is None or value == '':
        return default
    try:
        if isinstance(value, str):
            cleaned = value.strip().replace(',', '.').replace(' ', '')
            return Decimal(cleaned)
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _get_usd_try_rate():
    """Best-effort USD->TRY rate. Falls back to 1 if unavailable."""
    try:
        from accounting.services import get_exchange_rate
        rate = get_exchange_rate("USD", "TRY")
        if rate:
            return Decimal(str(rate))
    except Exception:
        pass
    return Decimal('1')


@method_decorator(login_required, name='dispatch')
class WarehouseList(View):
    template_name = "operating/warehouse_list.html"

    def get(self, request):
        warehouses = Warehouse.objects.annotate(
            n_products=Count('products'),
        ).order_by('name')
        return render(request, self.template_name, {
            'warehouses': warehouses,
        })


def _get_book_choices():
    """Return list of accounting Book objects for dropdown (lazy import)."""
    try:
        from accounting.models import Book
        return Book.objects.all().order_by('name')
    except Exception:
        return []


@method_decorator(login_required, name='dispatch')
class WarehouseCreate(View):
    template_name = "operating/warehouse_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            'warehouse': None,
            'books': _get_book_choices(),
        })

    def post(self, request):
        name = (request.POST.get('name') or '').strip()
        location = (request.POST.get('location') or '').strip()
        description = (request.POST.get('description') or '').strip()
        book_id = (request.POST.get('accounting_book') or '').strip()

        if not name:
            messages.error(request, "Name is required")
            return render(request, self.template_name, {
                'warehouse': None, 'books': _get_book_choices()
            })
        if Warehouse.objects.filter(name__iexact=name).exists():
            messages.error(request, "A warehouse with this name already exists")
            return render(request, self.template_name, {
                'warehouse': None, 'books': _get_book_choices()
            })

        book = None
        if book_id:
            try:
                from accounting.models import Book
                book = Book.objects.filter(pk=int(book_id)).first()
            except (ValueError, TypeError):
                pass

        wh = Warehouse.objects.create(
            name=name,
            location=location or None,
            description=description or None,
            accounting_book=book,
        )
        messages.success(request, f"Warehouse '{wh.name}' created")
        return redirect(reverse('operating:warehouse_detail', args=[wh.pk]))


@method_decorator(login_required, name='dispatch')
class WarehouseEdit(View):
    template_name = "operating/warehouse_form.html"

    def get(self, request, pk):
        warehouse = get_object_or_404(Warehouse, pk=pk)
        return render(request, self.template_name, {
            'warehouse': warehouse,
            'books': _get_book_choices(),
        })

    def post(self, request, pk):
        warehouse = get_object_or_404(Warehouse, pk=pk)
        name = (request.POST.get('name') or '').strip()
        location = (request.POST.get('location') or '').strip()
        description = (request.POST.get('description') or '').strip()
        book_id = (request.POST.get('accounting_book') or '').strip()

        if not name:
            messages.error(request, "Name is required")
            return render(request, self.template_name, {
                'warehouse': warehouse, 'books': _get_book_choices()
            })

        # Allow same name as own, but block conflict with others
        if Warehouse.objects.filter(name__iexact=name).exclude(pk=warehouse.pk).exists():
            messages.error(request, "Another warehouse with this name already exists")
            return render(request, self.template_name, {
                'warehouse': warehouse, 'books': _get_book_choices()
            })

        warehouse.name = name
        warehouse.location = location or None
        warehouse.description = description or None

        if book_id:
            try:
                from accounting.models import Book
                warehouse.accounting_book = Book.objects.filter(pk=int(book_id)).first()
            except (ValueError, TypeError):
                warehouse.accounting_book = None
        else:
            warehouse.accounting_book = None

        warehouse.save()
        messages.success(request, f"Warehouse '{warehouse.name}' updated")
        return redirect(reverse('operating:warehouse_detail', args=[warehouse.pk]))


SORT_OPTIONS = {
    'name_asc': ('name', 'Name (A → Z)'),
    'name_desc': ('-name', 'Name (Z → A)'),
    'qty_desc': ('-quantity', 'Quantity (high → low)'),
    'qty_asc': ('quantity', 'Quantity (low → high)'),
    'price_desc': ('-purchase_price', 'Unit price (high → low)'),
    'price_asc': ('purchase_price', 'Unit price (low → high)'),
    'total_usd_desc': ('-_total_usd', 'Total USD (high → low)'),
    'total_usd_asc': ('_total_usd', 'Total USD (low → high)'),
    'total_try_desc': ('-_total_try', 'Total TRY (high → low)'),
    'total_try_asc': ('_total_try', 'Total TRY (low → high)'),
    'recent': ('-updated_at', 'Recently updated'),
}


PAGE_SIZE = 50


@method_decorator(login_required, name='dispatch')
class WarehouseDetail(View):
    template_name = "operating/warehouse_detail.html"

    def get(self, request, pk):
        warehouse = get_object_or_404(Warehouse, pk=pk)
        search = (request.GET.get('search') or '').strip()
        sort = (request.GET.get('sort') or 'name_asc').strip()
        page_num = request.GET.get('page', '1')

        products = WarehouseProduct.objects.filter(warehouse=warehouse).annotate(
            _total_usd=F('quantity') * F('cost_usd'),
            _total_try=F('quantity') * F('cost_try'),
        )

        if search:
            from django.db.models import Q
            products = products.filter(
                Q(name__icontains=search) | Q(sku__icontains=search) | Q(barcode__icontains=search)
            )

        order_by = SORT_OPTIONS.get(sort, SORT_OPTIONS['name_asc'])[0]
        products = products.order_by(order_by, 'id')

        # Paginate AFTER filter+sort, BEFORE rendering
        paginator = Paginator(products, PAGE_SIZE)
        try:
            page = paginator.page(int(page_num))
        except (PageNotAnInteger, ValueError):
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages or 1)

        # Aggregate totals across the whole warehouse (independent of filter)
        all_products = WarehouseProduct.objects.filter(warehouse=warehouse)
        totals = all_products.aggregate(
            total_usd=Coalesce(
                Sum(F('quantity') * F('cost_usd'), output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal('0'), output_field=DecimalField(max_digits=18, decimal_places=2)),
            total_try=Coalesce(
                Sum(F('quantity') * F('cost_try'), output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal('0'), output_field=DecimalField(max_digits=18, decimal_places=2)),
            n=Count('id'),
            qty=Coalesce(Sum('quantity'), Decimal('0'), output_field=DecimalField(max_digits=18, decimal_places=2)),
        )

        ctx = {
            'warehouse': warehouse,
            'products': page.object_list,  # current page only
            'page': page,
            'paginator': paginator,
            'total_value_usd': totals['total_usd'],
            'total_value_try': totals['total_try'],
            'product_count': totals['n'],
            'total_quantity': totals['qty'],
            'search': search,
            'sort': sort,
            'sort_options': [(k, v[1]) for k, v in SORT_OPTIONS.items()],
            'filtered_count': paginator.count,
        }

        # HTMX partial refresh for search/sort/page — re-render rows + pagination together
        if request.headers.get('HX-Request'):
            return render(request, "operating/partials/warehouse_product_table_body.html", ctx)

        return render(request, self.template_name, ctx)


@method_decorator(login_required, name='dispatch')
class WarehouseProductImport(View):
    """Import products from Excel — streaming progress + bulk operations.

    Speed strategy:
      1. Read all rows in one pass (openpyxl read_only)
      2. Pre-fetch existing products for this warehouse, indexed by SKU
      3. Categorize each row: skip / update / create (compare quantity to skip unchanged)
      4. Use bulk_create + bulk_update (chunks of 1000)
      5. Stream progress as newline-delimited JSON

    Expected columns (case-insensitive TR/EN):
      Adı/Name, Kodu/SKU, Miktar/Quantity, Alış Fiyatı/Purchase Price,
      Para Birimi/Currency, Barkod (optional), Model (optional)
    """

    def post(self, request, pk):
        warehouse = get_object_or_404(Warehouse, pk=pk)
        upload = request.FILES.get('file')
        if not upload:
            return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)

        try:
            from openpyxl import load_workbook
        except ImportError:
            return JsonResponse({'success': False, 'error': 'openpyxl not installed'}, status=500)

        try:
            wb = load_workbook(upload, data_only=True, read_only=True)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Invalid xlsx: {e}'}, status=400)

        ws = wb.active

        # Find header row
        header_row = None
        rows_iter = ws.iter_rows(values_only=True)
        for row in rows_iter:
            if row and any(c is not None and str(c).strip() != '' for c in row):
                header_row = [str(c).strip().lower() if c is not None else '' for c in row]
                break

        if not header_row:
            return JsonResponse({'success': False, 'error': 'Empty sheet'}, status=400)

        def find_col(*candidates):
            for cand in candidates:
                cand = cand.lower()
                for i, h in enumerate(header_row):
                    if cand in h:
                        return i
            return None

        col_name = find_col('adı', 'adi', 'name', 'ürün adı', 'urun adi')
        col_sku = find_col('kodu', 'kod', 'sku', 'code')
        col_qty = find_col('miktar', 'quantity', 'qty', 'stok')
        col_price = find_col('alış fiyatı', 'alis fiyati', 'purchase price', 'a. fiyatı', 'a.fiyat')
        col_currency = find_col('para birimi', 'currency', 'a.f.b', 'döviz')
        col_barcode = find_col('barkod', 'barcode')
        col_model = find_col('model')

        if col_name is None or col_sku is None or col_qty is None or col_price is None:
            return JsonResponse({
                'success': False,
                'error': 'Required columns not found. Need: Name, Code/SKU, Quantity, Purchase Price.',
                'detected_headers': header_row,
            }, status=400)

        # Buffer all data rows into memory (fast — openpyxl read_only mode)
        data_rows = []
        for row in rows_iter:
            if row and any(c is not None and str(c).strip() != '' for c in row):
                data_rows.append(row)

        wb.close()
        total_rows = len(data_rows)

        if total_rows == 0:
            return JsonResponse({'success': True, 'created': 0, 'updated': 0, 'skipped': 0, 'unchanged': 0, 'total': 0})

        usd_to_try = _get_usd_try_rate()
        try_to_usd = (Decimal('1') / usd_to_try) if usd_to_try and usd_to_try != 0 else Decimal('0')

        # Pre-fetch existing rows once — by SKU
        existing_by_sku = {
            p.sku: p
            for p in WarehouseProduct.objects.filter(warehouse=warehouse).only(
                'id', 'sku', 'name', 'barcode', 'model', 'quantity',
                'purchase_price', 'purchase_currency', 'cost_usd', 'cost_try',
            )
            if p.sku
        }

        def stream():
            to_create = []
            to_update = []
            update_fields = ['name', 'barcode', 'model', 'quantity', 'purchase_price',
                             'purchase_currency', 'cost_usd', 'cost_try']

            counters = {'created': 0, 'updated': 0, 'unchanged': 0, 'skipped': 0}
            errors = []

            yield (json.dumps({'phase': 'start', 'total': total_rows}) + '\n').encode('utf-8')

            for idx, row in enumerate(data_rows, start=1):
                try:
                    name = row[col_name] if col_name < len(row) else None
                    sku = row[col_sku] if col_sku < len(row) else None

                    if not name or str(name).strip() == '':
                        counters['skipped'] += 1
                        continue

                    name = str(name).strip()
                    sku_str = str(sku).strip() if sku is not None else None

                    qty = _safe_decimal(row[col_qty] if col_qty < len(row) else None, Decimal('0'))
                    price = _safe_decimal(row[col_price] if col_price < len(row) else None)
                    currency_raw = row[col_currency] if (col_currency is not None and col_currency < len(row)) else None
                    barcode = row[col_barcode] if (col_barcode is not None and col_barcode < len(row)) else None
                    model = row[col_model] if (col_model is not None and col_model < len(row)) else None

                    barcode = str(barcode).strip() if barcode is not None else None
                    model = str(model).strip() if model is not None else None

                    # Currency
                    currency = 'USD'
                    if currency_raw is not None:
                        cu = str(currency_raw).strip().upper()
                        if 'TRY' in cu or 'TL' in cu or '₺' in cu:
                            currency = 'TRY'
                        elif 'EUR' in cu or '€' in cu:
                            currency = 'EUR'

                    # Costs
                    cost_usd = None
                    cost_try = None
                    if price is not None:
                        if currency == 'USD':
                            cost_usd = price
                            cost_try = price * usd_to_try
                        elif currency == 'TRY':
                            cost_try = price
                            cost_usd = price * try_to_usd
                        else:
                            cost_usd = price
                            cost_try = price * usd_to_try

                    existing = existing_by_sku.get(sku_str) if sku_str else None

                    if existing:
                        # Compare quantity (and price) — skip if unchanged
                        same_qty = (existing.quantity or 0) == (qty or 0)
                        same_price = (existing.purchase_price or 0) == (price or 0)
                        same_curr = (existing.purchase_currency or '') == currency
                        same_name = (existing.name or '') == name

                        if same_qty and same_price and same_curr and same_name:
                            counters['unchanged'] += 1
                        else:
                            existing.name = name
                            existing.barcode = barcode
                            existing.model = model
                            existing.quantity = qty
                            existing.purchase_price = price
                            existing.purchase_currency = currency
                            existing.cost_usd = cost_usd
                            existing.cost_try = cost_try
                            to_update.append(existing)
                            counters['updated'] += 1
                    else:
                        to_create.append(WarehouseProduct(
                            warehouse=warehouse,
                            name=name,
                            sku=sku_str,
                            barcode=barcode,
                            model=model,
                            quantity=qty,
                            purchase_price=price,
                            purchase_currency=currency,
                            cost_usd=cost_usd,
                            cost_try=cost_try,
                        ))
                        counters['created'] += 1

                except Exception as e:
                    errors.append(f"Row {idx}: {e}")
                    counters['skipped'] += 1

                # Stream progress every 200 rows
                if idx % 200 == 0 or idx == total_rows:
                    yield (json.dumps({
                        'phase': 'processing',
                        'current': idx,
                        'total': total_rows,
                        **counters,
                    }) + '\n').encode('utf-8')

            # Bulk write to DB
            yield (json.dumps({'phase': 'saving', 'message': 'Writing to database...'}) + '\n').encode('utf-8')

            if to_create:
                WarehouseProduct.objects.bulk_create(to_create, batch_size=1000, ignore_conflicts=False)

            if to_update:
                WarehouseProduct.objects.bulk_update(to_update, update_fields, batch_size=1000)

            yield (json.dumps({
                'phase': 'done',
                'success': True,
                'total': total_rows,
                **counters,
                'usd_to_try_rate': str(usd_to_try),
                'errors': errors[:10],
            }) + '\n').encode('utf-8')

        response = StreamingHttpResponse(stream(), content_type='application/x-ndjson')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


@method_decorator(login_required, name='dispatch')
class WarehouseDelete(View):
    def post(self, request, pk):
        warehouse = get_object_or_404(Warehouse, pk=pk)
        name = warehouse.name
        warehouse.delete()
        messages.success(request, f"Warehouse '{name}' deleted")
        return redirect(reverse('operating:warehouse_list'))
