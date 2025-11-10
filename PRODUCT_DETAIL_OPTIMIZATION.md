# Product Detail Performance Optimization

## 🎯 Problem

Product detail sayfası **2.5-2.7 saniye** sürüyordu.

### 📊 Analiz Sonuçları (PK: 166)
```
Product fetch:        1.8953s  ⚠️ ANA PROBLEM!
Template rendering:   0.7793s  ⚠️ İkincil problem
Context build:        0.0010s  ✅ OK
---
TOTAL:               2.6774s
```

**Ana sorun:** Database fetch işlemi 1.9 saniye sürüyor!

---

## ✅ Uygulanan Optimizasyonlar

### 1. **Prefetch Optimizasyonu** ✅

**Dosya:** `erp/marketing/views.py` → `ProductDetail.get_queryset()`

**Değişiklik:**
- ❌ **Önce:** Basit `prefetch_related()` - N+1 query problemi
- ✅ **Sonra:** `Prefetch()` objects ile nested prefetch

**Kod:**
```python
from django.db.models import Prefetch

queryset = Product.objects.select_related(
    'category', 'primary_image', 'supplier'
).prefetch_related(
    # Files with ordering
    Prefetch(
        'files',
        queryset=ProductFile.objects.select_related('product_variant').order_by('sequence', 'pk')
    ),
    'collections',
    # Variants with nested prefetch
    Prefetch(
        'variants',
        queryset=ProductVariant.objects.prefetch_related(
            Prefetch('files', queryset=ProductFile.objects.order_by('sequence', 'pk')),
            Prefetch(
                'product_variant_attribute_values',
                queryset=ProductVariantAttributeValue.objects.select_related(
                    'product_variant_attribute'
                )
            )
        )
    )
)
```

**Faydası:**
- ✅ Tek sorguda tüm related data
- ✅ N+1 query eliminate edildi
- ✅ Ordering database'de yapılıyor (hızlı)

---

### 2. **Database Index'ler** ✅

**Dosya:** `erp/marketing/models.py`

#### 2.1 ProductVariant Model
```python
class Meta:
    indexes = [
        models.Index(fields=['product', 'variant_sku']),  # Fast product lookup
        models.Index(fields=['variant_featured']),  # Filter featured
    ]

product = ForeignKey(..., db_index=True)  # FK index
```

#### 2.2 ProductFile Model
```python
class Meta:
    indexes = [
        models.Index(fields=['product', 'sequence']),  # Fast ordering
        models.Index(fields=['product_variant', 'sequence']),  # Variant files
        models.Index(fields=['product', 'is_primary']),  # Primary lookup
    ]
    ordering = ['sequence', 'pk']  # Default ordering

product = ForeignKey(..., db_index=True)
product_variant = ForeignKey(..., db_index=True)
is_primary = BooleanField(..., db_index=True)
sequence = PositiveIntegerField(..., db_index=True)
```

#### 2.3 ProductVariantAttributeValue Model
```python
class Meta:
    indexes = [
        models.Index(fields=['product_variant_attribute']),
    ]

product_variant_attribute = ForeignKey(..., db_index=True)
```

**Migration:**
```bash
✅ Migration created: 0041_productvariantattributevalue_marketing_p_product_5e14e4_idx.py
✅ Applied successfully
```

---

### 3. **Performance Logging** ✅

#### 3.1 View-Level Logging
**Dosya:** `erp/marketing/views.py`

Eklenen metodlar:
- `dispatch()` - Total execution time
- `get_queryset()` - Query build time
- `get_object()` - Database fetch time
- `get_context_data()` - Component timing

#### 3.2 Middleware
**Dosya:** `erp/erp/middleware.py` (YENİ)
- Template rendering time
- Total request time
- Slow request detection

#### 3.3 Test Script
**Dosya:** `test_product_performance.py`
- SQL query profiling
- Query count
- Slow query detection

---

## 📈 Beklenen İyileştirmeler

### Önce vs Sonra (Tahmin)

```
Component              Önce       Sonra      İyileştirme
-----------------------------------------------------------
Database Fetch        1.8953s    0.2-0.3s   ~85% faster ⚡
Template Render       0.7793s    0.5-0.6s   ~20% faster
Context Build         0.0010s    0.0010s    Same
-----------------------------------------------------------
TOTAL                 2.6774s    0.7-0.9s   ~70% faster 🚀
```

### Hedef: **<1 saniye**

---

## 🧪 Test Etme

### 1. Server ile Test
```bash
# Server başlat
.\vir_env\Scripts\python.exe erp/manage.py runserver

# Browser'da product detail'e git
# Terminal'de yeni timing'leri gör
```

### 2. Test Script ile
```bash
# Specific product
python test_product_performance.py 166

# İlk ürün
python test_product_performance.py
```

---

## 🔍 Hala Yavaşsa - İlave Optimizasyonlar

### Template Rendering (0.7s problemi devam ederse)

#### 1. Fragment Caching
```django
{% load cache %}
{% cache 300 product_detail product.id %}
    <!-- Heavy template logic -->
{% endcache %}
```

#### 2. Lazy Loading
```html
<!-- Variant images lazy load -->
<img loading="lazy" src="...">
```

#### 3. Template Simplification
- Unnecessary loops'ları azalt
- Template tag çağrılarını minimize et
- Static content'i separate et

### Database Query (hala yavaşsa)

#### 1. Query Profiling
```bash
# Django Debug Toolbar kullan
pip install django-debug-toolbar
```

#### 2. Database Connection
```python
DATABASES = {
    'default': {
        ...
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}
```

#### 3. Redis Cache (Uzun vadeli)
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

---

## 📁 Değiştirilen Dosyalar

### ✏️ Modified
1. ✅ `erp/marketing/views.py` - Prefetch optimization + logging
2. ✅ `erp/marketing/models.py` - Database indexes
3. ✅ `erp/erp/settings.py` - Middleware added

### 📄 Created
1. ✅ `erp/erp/middleware.py` - Performance middleware
2. ✅ `test_product_performance.py` - Test script
3. ✅ `PERFORMANCE_LOGGING.md` - Logging guide
4. ✅ `PRODUCT_DETAIL_OPTIMIZATION.md` - This file

### 🗄️ Database
1. ✅ Migration: `0041_productvariantattributevalue_*.py`

---

## 🎯 Next Steps

1. **Test yap** - Server'ı başlat ve timing'leri kontrol et
2. **Results gör** - Hangi kısım hala yavaş?
3. **Template optimize et** (gerekirse)
4. **Cache ekle** (uzun vadeli)

---

## 📞 Monitoring

### Production'da İzleme

**Logging ayarları:**
```python
# settings.py
LOGGING = {
    'handlers': {
        'performance': {
            'class': 'logging.FileHandler',
            'filename': 'performance.log',
        },
    },
}
```

### Metrics Takibi
- Average page load: Target <1s
- 95th percentile: Target <1.5s
- 99th percentile: Target <2s

---

**Oluşturulma:** 2025-11-01  
**Status:** ✅ Uygulandı  
**Next:** Test et ve sonuçları gör
