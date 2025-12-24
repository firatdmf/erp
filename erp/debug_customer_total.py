import os
import django
from django.conf import settings
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from operating.models import Order

def check_deene_orders():
    print("Checking orders for 'deene'...")
    
    # Filter like the view does
    # Assuming start_date covers enough time, let's just check ALL orders first
    all_orders = Order.objects.filter(web_client__name__icontains='deene')
    print(f"Total orders found: {all_orders.count()}")
    
    total_original_price = all_orders.aggregate(t=Sum('original_price'))['t']
    print(f"Total Sum(original_price) for all: {total_original_price}")
    
    # Check failed
    failed_orders = all_orders.filter(payment_status='failed')
    print(f"Failed orders: {failed_orders.count()}")
    
    # Check null original_price
    null_price = all_orders.filter(original_price__isnull=True)
    print(f"Null original_price: {null_price.count()}")
    
    # Apply view filters exactly
    # View excludes failed and null original_price
    valid_orders = all_orders.filter(original_price__isnull=False).exclude(payment_status='failed')
    print(f"Valid orders count: {valid_orders.count()}")
    valid_sum = valid_orders.aggregate(t=Sum('original_price'))['t']
    print(f"Valid Sum(original_price): {valid_sum}")
    
    # List first 10 valid orders
    print("\nTop 10 Valid Orders:")
    for o in valid_orders.order_by('-original_price')[:10]:
        print(f"ID: {o.id}, Created: {o.created_at}, Price: {o.original_price}, Status: {o.payment_status}")

if __name__ == "__main__":
    check_deene_orders()
