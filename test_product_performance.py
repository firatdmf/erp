"""
Performance test script for ProductDetail view
Run this to see detailed query logging
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'erp'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from marketing.views import ProductDetail
from marketing.models import Product
import time

# Enable Django query logging
import logging
from django.db import connection
from django.conf import settings

# Configure logging to show SQL queries
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('django.db.backends')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

def test_product_detail(product_pk=None):
    """
    Test ProductDetail view performance
    """
    # Get first product if no PK provided
    if product_pk is None:
        product = Product.objects.first()
        if not product:
            print("❌ No products found in database")
            return
        product_pk = product.pk
    
    print(f"\n🧪 Testing ProductDetail with Product PK: {product_pk}\n")
    
    # Create fake request
    factory = RequestFactory()
    request = factory.get(f'/marketing/product_detail/{product_pk}/')
    request.user = AnonymousUser()
    
    # Reset query counter
    connection.queries_log.clear()
    
    # Time the view
    start = time.time()
    
    view = ProductDetail.as_view()
    response = view(request, pk=product_pk)
    
    total_time = time.time() - start
    
    # Show query statistics
    print(f"\n\n" + "="*80)
    print(f"📊 DATABASE QUERY STATISTICS")
    print("="*80)
    print(f"Total Queries: {len(connection.queries)}")
    print(f"Total Time: {total_time:.4f}s")
    
    if connection.queries:
        print(f"\n📝 Query Breakdown:")
        query_times = []
        for i, query in enumerate(connection.queries, 1):
            query_time = float(query['time'])
            query_times.append(query_time)
            print(f"\n   Query #{i}: {query_time:.4f}s")
            print(f"   SQL: {query['sql'][:200]}...")
        
        print(f"\n⏱️  Query Time Stats:")
        print(f"   Total Query Time: {sum(query_times):.4f}s")
        print(f"   Average: {sum(query_times)/len(query_times):.4f}s")
        print(f"   Min: {min(query_times):.4f}s")
        print(f"   Max: {max(query_times):.4f}s")
        
        # Find slow queries
        slow_queries = [q for q in connection.queries if float(q['time']) > 0.1]
        if slow_queries:
            print(f"\n⚠️  SLOW QUERIES (>100ms): {len(slow_queries)}")
            for i, query in enumerate(slow_queries, 1):
                print(f"\n   Slow Query #{i}: {float(query['time']):.4f}s")
                print(f"   {query['sql'][:300]}")
    
    print("\n" + "="*80 + "\n")
    
    return response

if __name__ == "__main__":
    # Test with specific product or first available
    product_pk = int(sys.argv[1]) if len(sys.argv) > 1 else None
    test_product_detail(product_pk)
