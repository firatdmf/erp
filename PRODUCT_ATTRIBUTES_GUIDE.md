# Product Attributes System

## Özellik
Product ve Variant'lara özel özellikler (attributes) ekleyebilirsiniz.

### Kullanım Alanları
- **Kumaş Ürünleri:** En, boy, kumaş türü (tül, grek, ttm), kullanım alanı (gelinlik, masa örtüsü, perde)
- **Desenli/Düz:** Düz kumaş mı, desenli brode mi
- **Diğer:** Herhangi bir ürün özelliği

## Database Yapısı

### ProductAttribute Model
```python
class ProductAttribute(models.Model):
    name = models.CharField(max_length=255)   # Özellik adı: "En", "Kumaş Türü"
    value = models.CharField(max_length=500)  # Değer: "150cm", "Tül"
    
    # İkisinden biri zorunlu (aynı anda ikisi olamaz)
    product = models.ForeignKey(Product)           # Ana ürün
    product_variant = models.ForeignKey(ProductVariant)  # Variant
    
    sequence = models.PositiveIntegerField()  # Sıralama
```

### İlişkiler
```
Product → ProductAttribute (1:N)
ProductVariant → ProductAttribute (1:N)
```

## Kullanım

### 1. Product Attributes (Ana Ürün)
Product form'da "Product Attributes" section'ı kullanın:

```
[Özellik Adı]  [Özellik Değeri]  [🗑️]
En             150cm              
Kumaş Türü     Tül                
Kullanım       Gelinlik           

[+ Add Attribute]
```

**Backend'e gönderilen veri:**
```
attribute_names[] = ["En", "Kumaş Türü", "Kullanım"]
attribute_values[] = ["150cm", "Tül", "Gelinlik"]
```

### 2. Variant Attributes (Variant'a özel değerler)
Variant table'da her variant için attributes override edilebilir.

**variants_json yapısı:**
```json
{
  "product_variant_list": [
    {
      "variant_sku": "TUL-BEYAZ-150",
      "variant_attribute_values": {
        "color": "beyaz",
        "size": "150cm"
      },
      "product_attributes": [
        {"name": "En", "value": "150cm"},
        {"name": "Kumaş Türü", "value": "Tül"},
        {"name": "Kullanım", "value": "Gelinlik"}
      ]
    },
    {
      "variant_sku": "TUL-BEYAZ-200",
      "product_attributes": [
        {"name": "En", "value": "200cm"},  // Farklı en
        {"name": "Kumaş Türü", "value": "Tül"},
        {"name": "Kullanım", "value": "Perde"}  // Farklı kullanım
      ]
    }
  ]
}
```

## Backend İşlem Akışı

### ProductCreate / ProductEdit

```python
# 1. Product attributes
self.handle_attributes(self.object)
    → POST'tan attribute_names[] ve attribute_values[] alır
    → Mevcut attributes'ları siler
    → Yeni attributes oluşturur

# 2. Variant attributes
self.handle_variants(self.object, variants_json)
    → Her variant için product_attributes array'ini kontrol eder
    → Variant'ın mevcut attributes'ları siler
    → Yeni attributes oluşturur
```

### handle_attributes metodu
```python
def handle_attributes(self, product):
    attribute_names = self.request.POST.getlist('attribute_names[]')
    attribute_values = self.request.POST.getlist('attribute_values[]')
    
    # Clear old
    product.attributes.all().delete()
    
    # Create new
    for idx, (name, value) in enumerate(zip(attribute_names, attribute_values)):
        ProductAttribute.objects.create(
            product=product,
            name=name,
            value=value,
            sequence=idx
        )
```

### handle_variants içinde (variant attributes)
```python
for variant_data in variants_data:
    variant_product_attrs = variant_data.get("product_attributes", [])
    
    # Clear old
    variant.attributes.all().delete()
    
    # Create new
    for idx, attr_data in enumerate(variant_product_attrs):
        ProductAttribute.objects.create(
            product_variant=variant,
            name=attr_data["name"],
            value=attr_data["value"],
            sequence=idx
        )
```

## Frontend Kullanımı

### Product Attributes Section (product_form.html)
```html
<div id="product_attributes_container">
  <!-- Her attribute için bir satır -->
  <div class="attribute-row">
    <input name="attribute_names[]" placeholder="Özellik Adı">
    <input name="attribute_values[]" placeholder="Özellik Değeri">
    <button onclick="removeProductAttribute(this)">🗑️</button>
  </div>
</div>

<button onclick="addProductAttribute()">+ Add Attribute</button>
```

### JavaScript Fonksiyonlar
```javascript
function addProductAttribute() {
    // Yeni attribute row ekle
}

function removeProductAttribute(button) {
    // Attribute row'u sil
}
```

## Örnek: Kumaş Ürünü

### Product Attributes (Tüm ürün için geçerli)
```
En: 150cm
Kumaş Türü: Tül
Desen: Düz
```

### Variant 1: Beyaz - 150cm
```
variant_sku: TUL-BEYAZ-150
variant_attribute_values: {color: beyaz, size: 150cm}
product_attributes: [
  {name: "En", value: "150cm"},
  {name: "Kumaş Türü", value: "Tül"},
  {name: "Kullanım", value: "Gelinlik"}
]
```

### Variant 2: Beyaz - 200cm
```
variant_sku: TUL-BEYAZ-200
variant_attribute_values: {color: beyaz, size: 200cm}
product_attributes: [
  {name: "En", value: "200cm"},          ← Farklı
  {name: "Kumaş Türü", value: "Tül"},
  {name: "Kullanım", value: "Perde"}    ← Farklı
]
```

### Variant 3: Kırmızı - 150cm
```
variant_sku: TUL-KIRMIZI-150
variant_attribute_values: {color: kırmızı, size: 150cm}
product_attributes: [
  {name: "En", value: "150cm"},
  {name: "Kumaş Türü", value: "Brode"}, ← Farklı (desenli)
  {name: "Kullanım", value: "Gelinlik"}
]
```

## API Endpoints

Attribute'lar product/variant create/edit endpoint'lerinde otomatik işlenir:
- `POST /marketing/product_create/`
- `POST /marketing/product_edit/<pk>/`

## Admin Panel

ProductAttribute modeli admin'e eklenebilir:

```python
# marketing/admin.py
from marketing.models import ProductAttribute

@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'value', 'get_parent', 'sequence']
    list_filter = ['name']
    search_fields = ['name', 'value']
    
    def get_parent(self, obj):
        return obj.product or obj.product_variant
    get_parent.short_description = 'Parent'
```

## Querying

### Product'ın attributes'ları
```python
product = Product.objects.get(pk=1)
attributes = product.attributes.all()

for attr in attributes:
    print(f"{attr.name}: {attr.value}")
```

### Variant'ın attributes'ları
```python
variant = ProductVariant.objects.get(pk=1)
attributes = variant.attributes.all()

for attr in attributes:
    print(f"{attr.name}: {attr.value}")
```

### Prefetch ile optimize etme
```python
products = Product.objects.prefetch_related('attributes').all()

for product in products:
    for attr in product.attributes.all():  # No N+1 query!
        print(attr.name, attr.value)
```

## Migration

```bash
python manage.py makemigrations marketing
python manage.py migrate marketing
```

## Test

```python
from marketing.models import Product, ProductAttribute

# Product attribute oluştur
product = Product.objects.first()
ProductAttribute.objects.create(
    product=product,
    name="En",
    value="150cm",
    sequence=0
)

# Variant attribute oluştur
variant = product.variants.first()
ProductAttribute.objects.create(
    product_variant=variant,
    name="En",
    value="200cm",  # Override
    sequence=0
)
```

## Kısıtlamalar

1. **Tek parent:** Attribute ya product'a ya da variant'a ait olabilir (ikisine birden değil)
2. **Clean validation:** Model'de `clean()` metodu bu kısıtlamayı kontrol eder
3. **Delete cascade:** Product veya Variant silinirse attributes'ları da silinir

---

**Created:** 2025-11-24
**Status:** ✅ Implemented
**Version:** 1.0
