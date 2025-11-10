import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'erp'))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')

# Setup Django
django.setup()

from django.db import connection, reset_queries
from django.test.utils import override_settings
from marketing.models import Product

# Enable query logging
@override_settings(DEBUG=True)
def test_product_detail():
    reset_queries()
    
    # Get product
    product_id = 166  # Change this to your test product ID
    
    print(f"\n{'='*80}")
    print(f"Testing ProductDetail Query Performance - Product ID: {product_id}")
    print(f"{'='*80}\n")
    
    # Simulate the view's queryset
    from django.db.models import Prefetch
    from marketing.models import ProductFile, ProductVariant, ProductVariantAttributeValue
    
    queryset = Product.objects.select_related(
        'category',
        'primary_image',
        'supplier'
    ).prefetch_related(
        Prefetch(
            'files',
            queryset=ProductFile.objects.select_related('product_variant').order_by('sequence', 'pk')
        ),
        'collections',
        Prefetch(
            'variants',
            queryset=ProductVariant.objects.prefetch_related(
                Prefetch(
                    'files',
                    queryset=ProductFile.objects.order_by('sequence', 'pk')
                ),
                Prefetch(
                    'product_variant_attribute_values',
                    queryset=ProductVariantAttributeValue.objects.select_related(
                        'product_variant_attribute'
                    )
                )
            )
        )
    )
    
    # Fetch product
    product = queryset.get(pk=product_id)
    
    # Access variants and their data (simulating template access)
    variants = list(product.variants.all())
    print(f"✓ Product has {len(variants)} variants")
    
    for v in variants:
        files = list(v.files.all())
        attrs = list(v.product_variant_attribute_values.all())
        print(f"  - Variant {v.variant_sku}: {len(files)} files, {len(attrs)} attributes")
    
    # Show query count
    queries = connection.queries
    print(f"\n{'='*80}")
    print(f"TOTAL QUERIES: {len(queries)}")
    print(f"{'='*80}\n")
    
    # Show slow queries (>50ms)
    print("Slow queries (>50ms):")
    for i, query in enumerate(queries, 1):
        time_ms = float(query['time']) * 1000
        if time_ms > 50:
            print(f"{i}. {time_ms:.2f}ms - {query['sql'][:100]}...")
    
    print(f"\n{'='*80}\n")

if __name__ == '__main__':
    test_product_detail()
