from marketing.models import ProductAttribute, ProductVariantAttribute, ProductVariantAttributeValue, Product

print("\n" + "="*50)
print("🔍 CHECKING ATTRIBUTES IN DATABASE")
print("="*50)

# 1. Check Product Attributes (Directly on Product)
print("\n1. Checking ProductAttribute (Product.attributes):")
p_attrs = ProductAttribute.objects.filter(name__icontains='fabric').values('name', 'value', 'product__sku')
if p_attrs:
    for attr in p_attrs:
        print(f"   - Found: Name='{attr['name']}', Value='{attr['value']}' (Product SKU: {attr['product__sku']})")
else:
    print("   - No ProductAttribute found containing 'fabric'")

# 2. Check Product Variant Attributes
print("\n2. Checking ProductVariantAttribute:")
pv_attrs = ProductVariantAttribute.objects.filter(name__icontains='fabric')
if pv_attrs:
    for attr in pv_attrs:
        print(f"   - Found Attribute Name: '{attr.name}'")
        # Get values for this attribute
        values = ProductVariantAttributeValue.objects.filter(product_variant_attribute=attr).values_list('product_variant_attribute_value', flat=True).distinct()
        print(f"     Values: {list(values)}")
else:
    print("   - No ProductVariantAttribute found containing 'fabric'")

print("\n" + "="*50 + "\n")
