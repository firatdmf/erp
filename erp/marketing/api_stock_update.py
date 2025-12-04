"""
Stock update API for product variants after successful order creation.
Updates variant_quantity when orders are completed.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal

from .models import Product, ProductVariant


@require_http_methods(["POST"])
@csrf_exempt
def update_product_stock(request):
    """
    Update product or variant stock after successful order.
    
    Expects JSON:
    {
        "product_sku": "SKU123",
        "variant_sku": "VAR-SKU123" (optional),
        "quantity_change": -2.5  (negative = decrease, positive = increase)
    }
    
    If variant_sku is provided, updates variant_quantity.
    Otherwise, updates product quantity.
    
    Returns:
    {
        "success": true,
        "product_sku": "SKU123",
        "variant_sku": "VAR-SKU123" (if applicable),
        "old_quantity": 10.5,
        "new_quantity": 8.0,
        "quantity_changed": -2.5,
        "updated_type": "variant" or "product"
    }
    """
    try:
        data = json.loads(request.body)
        product_sku = data.get('product_sku')
        variant_sku = data.get('variant_sku')
        quantity_change = data.get('quantity_change', 0)
        
        if not product_sku:
            return JsonResponse({
                'success': False,
                'error': 'product_sku is required'
            }, status=400)
        
        quantity_change = Decimal(str(quantity_change))
        
        # Get product
        try:
            product = Product.objects.get(sku=product_sku)
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Product with SKU {product_sku} not found'
            }, status=404)
        
        # If variant_sku provided, update variant_quantity; otherwise update product quantity
        updated_type = 'product'
        
        if variant_sku:
            try:
                variant = ProductVariant.objects.get(variant_sku=variant_sku, product=product)
                old_quantity = variant.variant_quantity or Decimal('0')
                new_quantity = old_quantity + quantity_change
                
                # Don't allow negative stock
                if new_quantity < 0:
                    new_quantity = Decimal('0')
                
                variant.variant_quantity = new_quantity
                variant.save(update_fields=['variant_quantity'])
                updated_type = 'variant'
                
                print(f"✅ Stock updated for variant {variant_sku}: {old_quantity} -> {new_quantity} (change: {quantity_change})")
            except ProductVariant.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Variant with SKU {variant_sku} not found'
                }, status=404)
        else:
            # Update product quantity
            old_quantity = product.quantity or Decimal('0')
            new_quantity = old_quantity + quantity_change
            
            # Don't allow negative stock
            if new_quantity < 0:
                new_quantity = Decimal('0')
            
            product.quantity = new_quantity
            product.save(update_fields=['quantity'])
            
            print(f"✅ Stock updated for product {product_sku}: {old_quantity} -> {new_quantity} (change: {quantity_change})")
        
        return JsonResponse({
            'success': True,
            'product_sku': product_sku,
            'variant_sku': variant_sku if variant_sku else None,
            'old_quantity': str(old_quantity),
            'new_quantity': str(new_quantity),
            'quantity_changed': str(quantity_change),
            'updated_type': updated_type
        }, status=200)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid quantity_change: {str(e)}'
        }, status=400)
    
    except Exception as e:
        print(f"❌ Stock update error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
