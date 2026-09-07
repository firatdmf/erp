"""
Stock update API — now read-only.

This endpoint used to add `quantity_change` to ProductVariant.variant_quantity
(or Product.quantity) after an order was placed. Those columns are gone: a
catalog product's stock is the sum of the WarehouseProduct rows behind its
variants, read at the moment it is asked for, and the warehouse is the only
place a metre is ever added or removed.

So there is nothing here to write to, and the request is REFUSED rather than
silently accepted — a caller that believed it had booked stock and had not
would be worse than an error. The refusal carries the variant's live quantity
so the caller can reconcile against the real number, and 409 (not 404) so it
reads as "this is no longer how stock moves", not "your SKU is wrong".

Stock leaves the shelf when an order's reserved rolls are consumed at ship
time (operating.OrderStockReservation), which is a warehouse operation.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Product, ProductVariant


@require_http_methods(["POST"])
@csrf_exempt
def update_product_stock(request):
    """Refuse a stock write and report what the warehouse actually holds.

    Expects the same JSON the write API took:
    {
        "product_sku": "SKU123",
        "variant_sku": "VAR-SKU123" (optional),
        "quantity_change": -2.5
    }

    Always returns 409 for a resolvable product, with:
    {
        "success": false,
        "error": "...",
        "product_sku": "SKU123",
        "variant_sku": "VAR-SKU123" or null,
        "live_quantity": 2035.6 or null,   # null = no warehouse carries it
        "stock_tracked": true/false
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    product_sku = data.get('product_sku')
    variant_sku = data.get('variant_sku')

    if not product_sku:
        return JsonResponse({
            'success': False,
            'error': 'product_sku is required',
        }, status=400)

    try:
        product = Product.objects.get(sku=product_sku)
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Product with SKU {product_sku} not found',
        }, status=404)

    if variant_sku:
        try:
            target = ProductVariant.objects.get(variant_sku=variant_sku, product=product)
        except ProductVariant.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Variant with SKU {variant_sku} not found',
            }, status=404)
        tracked = target.stock_tracked
    else:
        target = product
        tracked = target.live_quantity is not None

    live = target.live_quantity
    return JsonResponse({
        'success': False,
        'error': ('Catalog stock is no longer writable. A variant\'s quantity is '
                  'the sum of the warehouse rows behind it, so stock is added or '
                  'removed in the warehouse, not through this endpoint. Metres '
                  'leave the shelf when an order\'s reserved rolls are consumed '
                  'at ship time.'),
        'product_sku': product_sku,
        'variant_sku': variant_sku or None,
        'live_quantity': float(live) if live is not None else None,
        'stock_tracked': tracked,
    }, status=409)
