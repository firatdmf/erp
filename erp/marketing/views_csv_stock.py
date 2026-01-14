"""
CSV Stock Update View
Uploads a CSV file and updates ProductVariant stock quantities.
CSV Format: Kodu (SKU), Miktar (Quantity)
"""

import csv
import io
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from .models import ProductVariant


def parse_turkish_decimal(value):
    """
    Parse Turkish decimal format (comma as decimal separator)
    Examples: "40,20" -> 40.20, "1.234,56" -> 1234.56
    """
    if not value:
        return Decimal('0')
    
    # Remove thousand separators (dots) and replace comma with dot
    value = str(value).strip()
    value = value.replace('.', '').replace(',', '.')
    
    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal('0')


@login_required
@require_POST
@csrf_protect
def csv_stock_update(request):
    """
    Process uploaded CSV and update ProductVariant quantities.
    
    Expected CSV columns:
    - Kodu: Product/Variant SKU code
    - Miktar: Stock quantity (Turkish decimal format)
    
    Returns JSON with update results.
    """
    
    if 'csv_file' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': 'No CSV file uploaded'
        }, status=400)
    
    csv_file = request.FILES['csv_file']
    
    # Validate file type
    if not csv_file.name.endswith('.csv'):
        return JsonResponse({
            'success': False,
            'error': 'Only CSV files are accepted'
        }, status=400)
    
    try:
        # Read raw bytes from file
        raw_content = csv_file.read()
        
        # Try multiple encodings (Turkish Windows files often use cp1254)
        file_content = None
        encodings_to_try = ['utf-8-sig', 'utf-8', 'cp1254', 'latin-1', 'cp1252', 'iso-8859-9']
        
        for encoding in encodings_to_try:
            try:
                file_content = raw_content.decode(encoding)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        
        if file_content is None:
            return JsonResponse({
                'success': False,
                'error': 'Could not decode file. Please save as UTF-8 and try again.'
            }, status=400)
        
        # Try different delimiters
        dialect = csv.Sniffer().sniff(file_content[:2048], delimiters=';,\t')
        reader = csv.DictReader(io.StringIO(file_content), delimiter=dialect.delimiter)
        
        # Normalize column names (handle variations)
        csv_data = {}
        total_rows = 0
        
        for row in reader:
            total_rows += 1
            
            # Find code column (case insensitive)
            code = None
            quantity = None
            
            for key, value in row.items():
                if key is None:
                    continue
                key_lower = key.lower().strip()
                
                if key_lower in ['kodu', 'kod', 'code', 'sku', 'stok kodu', 'ürün kodu']:
                    code = value.strip() if value else None
                elif key_lower in ['miktar', 'quantity', 'stok', 'adet', 'rezerv sonrası mikta']:
                    quantity = parse_turkish_decimal(value)
            
            if code:
                csv_data[code] = quantity
        
        if not csv_data:
            return JsonResponse({
                'success': False,
                'error': 'No valid data found in CSV. Required columns: "Kodu" and "Miktar"'
            }, status=400)
        
        # Match with ProductVariants
        matched_count = 0
        updated_count = 0
        not_found = []
        updated_variants = []
        
        # Get all variants that match any of the CSV codes
        variants = ProductVariant.objects.filter(variant_sku__in=csv_data.keys())
        variant_map = {v.variant_sku: v for v in variants}
        
        for code, new_quantity in csv_data.items():
            if code in variant_map:
                matched_count += 1
                variant = variant_map[code]
                old_quantity = variant.variant_quantity or Decimal('0')
                
                # Only update if quantity changed
                if old_quantity != new_quantity:
                    variant.variant_quantity = new_quantity
                    variant.save(update_fields=['variant_quantity'])
                    updated_count += 1
                    updated_variants.append({
                        'sku': code,
                        'old': str(old_quantity),
                        'new': str(new_quantity)
                    })
            else:
                not_found.append(code)
        
        return JsonResponse({
            'success': True,
            'total_rows': total_rows,
            'matched': matched_count,
            'updated': updated_count,
            'not_found_count': len(not_found),
            'not_found': not_found[:20],  # Limit to first 20
            'updated_variants': updated_variants[:20],  # Show first 20 updates
            'message': f'{updated_count} variant(s) stock updated'
        })
        
    except UnicodeDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Could not read file. Please try saving as UTF-8.'
        }, status=400)
    except csv.Error as e:
        return JsonResponse({
            'success': False,
            'error': f'CSV parse error: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)
