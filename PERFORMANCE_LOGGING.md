# Product Detail Performance Logging

## 🎯 Amaç

Product detail sayfasının 2.5 saniye sürmesinin nedenini bulmak için detaylı performance logging sistemi eklendi.

## 📝 Yapılan Değişiklikler

### 1. **ProductDetail View Logging** ✅
**Dosya:** `erp/marketing/views.py`

Eklenen metodlar:
- `dispatch()`: Total view execution time
- `get_queryset()`: Queryset build time
- `get_object()`: Database fetch time
- `get_context_data()`: Context building time (variants, files, collections)

### 2. **Performance Middleware** ✅
**Dosya:** `erp/erp/middleware.py` (YENİ)

Özellikler:
- Template rendering time
- Total request time
- Slow request detection (>500ms)

### 3. **Test Script** ✅
**Dosya:** `test_product_performance.py` (YENİ)

Özellikler:
- Database query sayısı
- Her query'nin süresi
- Yavaş query detection (>100ms)
- Query breakdown

## 🚀 Kullanım

### 1. Development Server ile Test

```bash
# Server'ı başlat
python erp/manage.py runserver

# Browser'da product detail sayfasına git
# Terminal'de detaylı logları göreceksiniz:
```

**Örnek Log Çıktısı:**
```
================================================================================
🔍 ProductDetail View Started - PK: 123
================================================================================

📊 Building queryset...
   ✓ Queryset built: 0.0012s

🔎 Fetching product object...
   ✓ Product fetched: 0.1245s
   📦 Product: iPhone 15 Pro (SKU: IPH-15-PRO)

🏗️  Building context data...
   ✓ Variants loaded: 0.0523s (4 variants)
   ✓ Files loaded: 0.0234s (8 files)
   ✓ Collections loaded: 0.0012s (2 collections)
   ✓ Variant details loaded: 0.1234s
   ⏱️  Context built: 0.2003s

🎨 Template Rendering: 1.8234s
   📄 Template: marketing/product_detail.html

================================================================================
⏱️  TOTAL VIEW TIME: 2.1482s
================================================================================

⚠️  SLOW REQUEST DETECTED!
   🌐 Path: /marketing/product_detail/123/
   ⏱️  Total Time: 2.1482s
```

### 2. Test Script ile Detaylı Analiz

```bash
# İlk ürünle test
python test_product_performance.py

# Belirli ürünle test
python test_product_performance.py 123
```

**Örnek Çıktı:**
```
🧪 Testing ProductDetail with Product PK: 123

================================================================================
📊 DATABASE QUERY STATISTICS
================================================================================
Total Queries: 12
Total Time: 2.1482s

📝 Query Breakdown:

   Query #1: 0.0234s
   SQL: SELECT "marketing_product"."id", "marketing_product"."title"...

   Query #2: 0.1523s
   SQL: SELECT "marketing_productvariant"."id", "marketing_productvariant"...

⏱️  Query Time Stats:
   Total Query Time: 0.3234s
   Average: 0.0269s
   Min: 0.0012s
   Max: 0.1523s

⚠️  SLOW QUERIES (>100ms): 1

   Slow Query #1: 0.1523s
   SELECT "marketing_productvariant"...
```

## 🔍 Yavaşlık Nedenleri (Olası)

### 1. **Database Query Issues**
- N+1 query problemi
- Missing indexes
- Yavaş JOINs
- Çok fazla prefetch

### 2. **Template Rendering**
- Karmaşık template logic
- Çok fazla loop
- Heavy templatetags
- Unoptimized image URLs

### 3. **Context Processing**
- Variant attribute values yükleme
- File URL generation (Cloudinary)
- Collection processing

### 4. **Network Issues**
- Cloudinary API calls
- Yavaş database connection
- External API calls

## 🛠️ Optimizasyon Önerileri

### Hemen Yapılabilir:
1. **Query Optimization**
   - `select_related()` ve `prefetch_related()` optimize et
   - Database indexler ekle
   - Unnecessary queries kaldır

2. **Template Optimization**
   - Fragment caching ekle
   - Template logic azalt
   - Lazy loading kullan

3. **Cloudinary Optimization**
   - URL transformation cache
   - Thumbnail pre-generation
   - CDN settings optimize

### Uzun Vadeli:
1. **Redis Cache**
   - Product data cache
   - Template fragment cache
   - Query result cache

2. **Database Optimization**
   - Indexes review
   - Query profiling
   - Connection pooling

3. **Frontend Optimization**
   - Lazy load images
   - Infinite scroll variants
   - Progressive enhancement

## 📊 Monitoring

### Production'da Aktif Et

**settings.py:**
```python
# Sadece DEBUG=True iken aktif
if DEBUG:
    MIDDLEWARE += ['erp.middleware.PerformanceLoggingMiddleware']
```

### Logları Sakla

**settings.py:**
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'performance.log',
        },
    },
    'loggers': {
        'performance': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

## 🎯 Next Steps

1. **Run test script** and identify slow queries
2. **Analyze template rendering** time
3. **Check Cloudinary** API response times
4. **Add database indexes** if needed
5. **Implement caching** for hot paths
6. **Profile variant loading** specifically

## 📞 Destek

Sonuçları görmek için:
```bash
# Server loglarını izle
python erp/manage.py runserver

# Test script çalıştır
python test_product_performance.py
```

---

**Oluşturulma Tarihi:** 2025-11-01  
**Durum:** ✅ Aktif  
**Sonraki Adım:** Test script çalıştır ve sonuçları analiz et
