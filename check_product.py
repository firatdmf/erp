from marketing.models import Product

print("\n" + "="*50)
print("🔍 CHECKING PRODUCT LZ2010")
print("="*50)

try:
    p = Product.objects.get(sku='LZ2010')
    print(f"Product: {p.title} (SKU: {p.sku})")
    print(f" - Featured: {p.featured}")
    print(f" - Category: {p.category.name if p.category else 'None'}")
    print(f" - Attributes: {list(p.attributes.values('name', 'value'))}")
except Product.DoesNotExist:
    print("❌ Product LZ2010 not found!")

print("\n" + "="*50 + "\n")
