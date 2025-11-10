# Primary Image Auto-Update Feature

## 🎯 Özellik

Product edit sayfasında **primary_image otomatik güncellenir**:

### Davranış:

```
✅ VARYANT VAR İSE:
   └─> primary_image = İlk varyantın ilk görseli (sequence=0)

✅ VARYANT YOK İSE:
   └─> primary_image = Product'ın ilk görseli (sequence=0)
```

---

## 🔧 Uygulama Yerleri

### 1. **ProductEdit.form_valid()** ✅
**Dosya:** `marketing/views.py` (satır ~955-985)

**Ne zaman çalışır:**
- Product update edildiğinde
- Varyant eklendiğinde/silindiğinde
- Görsel sequence değiştiğinde

**Logic:**
```python
# 1. Varyant var mı?
first_variant = product.variants.order_by('id').first()

if first_variant:
    # İlk varyantın ilk görselini al
    first_file = ProductFile.objects.filter(
        product_variant=first_variant
    ).order_by('sequence', 'pk').first()
    
    product.primary_image = first_file
else:
    # Varyant yok, product'ın ilk görselini al
    first_file = ProductFile.objects.filter(
        product=product,
        product_variant__isnull=True
    ).order_by('sequence', 'pk').first()
    
    product.primary_image = first_file
```

---

### 2. **instant_upload_file()** ✅
**Dosya:** `marketing/views.py` (satır ~1112-1127)

**Ne zaman çalışır:**
- Variant'a yeni görsel yüklendiğinde (instant upload)

**Logic:**
```python
# Varyant görseli yüklendiğinde
if variant:
    first_variant = product.variants.order_by('id').first()
    first_variant_file = ProductFile.objects.filter(
        product_variant=first_variant
    ).order_by('sequence', 'pk').first()
    
    if first_variant_file:
        product.primary_image = first_variant_file
```

---

### 3. **instant_delete_file()** ✅
**Dosya:** `marketing/views.py` (satır ~1170-1201)

**Ne zaman çalışır:**
- Görsel silindiğinde (instant delete)
- Silinen görsel primary_image ise

**Logic:**
```python
# Dosya silindikten SONRA
product = deleted_file.product
first_variant = product.variants.order_by('id').first()

if first_variant:
    # Varyant varsa ilk varyant görselini kullan
    first_variant_file = ...
    product.primary_image = first_variant_file or None
else:
    # Varyant yoksa product görselini kullan
    first_product_file = ...
    product.primary_image = first_product_file or None
```

---

## 📊 Test Senaryoları

### Test 1: Varyantlı Product
```
1. Product oluştur (SKU: TEST-001)
2. 2 varyant ekle:
   - Variant 1 (Red): 3 görsel
   - Variant 2 (Blue): 2 görsel
3. Product update et

✅ Beklenen: primary_image = Variant 1'in ilk görseli
```

### Test 2: Varyant Ekleme
```
1. Product var (varyant yok)
2. Product'a 3 görsel yükle
3. 1 varyant ekle + 2 görsel yükle
4. Save

✅ Beklenen: primary_image = Yeni varyantın ilk görseli
```

### Test 3: Varyant Silme
```
1. Product + 2 varyant var
2. İlk varyantı sil
3. Save

✅ Beklenen: primary_image = 2. varyantın ilk görseli (artık o ilk)
```

### Test 4: Görsel Silme (Instant Delete)
```
1. Product + varyant var
2. İlk varyantın ilk görselini sil (instant delete)

✅ Beklenen: primary_image = İlk varyantın 2. görseli (veya başka varyant)
```

### Test 5: Varyant Yok
```
1. Product var (varyant yok)
2. Product'a 3 görsel ekle
3. Görselleri yeniden sırala (drag & drop)
4. Save

✅ Beklenen: primary_image = sequence=0 olan görsel
```

---

## 🔍 Debug/Console Output

Değişiklikler console'da loglanır:

```bash
# ProductEdit.form_valid():
✓ Auto-updated primary_image to first variant's image (id=123)
⏱️  Primary image update: 0.015s

# instant_upload_file():
✓ Updated product primary to first variant's image 456

# instant_delete_file():
# (Sessiz - sadece update yapar)
```

---

## ⚠️ Dikkat Edilmesi Gerekenler

### 1. **"İlk Varyant" Tanımı**
```python
first_variant = product.variants.order_by('id').first()
```
- İlk oluşturulan varyant (ID'ye göre)
- NOT: SKU, name veya başka field'a göre DEĞİL

### 2. **"İlk Görsel" Tanımı**
```python
first_file = ProductFile.objects.filter(...).order_by('sequence', 'pk').first()
```
- sequence=0 olan görsel
- Aynı sequence varsa ID'ye göre (pk)

### 3. **NULL Primary Image**
Eğer hiç görsel yoksa:
```python
product.primary_image = None  # Allowed
```

### 4. **Performance**
- Single query per update (~10-15ms)
- `update_fields=['primary_image']` kullanılıyor (hızlı)
- Transaction içinde (atomic)

---

## 🚀 Kullanım Örnekleri

### Örnek 1: Varyant Öncelikli Product
```
Product: T-Shirt (SKU: TSHIRT-001)
├─ Variant 1: Red-M
│  ├─ Image 1 (seq=0) ← PRIMARY_IMAGE olur
│  ├─ Image 2 (seq=1)
│  └─ Image 3 (seq=2)
├─ Variant 2: Blue-L
│  ├─ Image 1 (seq=0)
│  └─ Image 2 (seq=1)
└─ Product images: (boş veya görmezden gelinir)
```

### Örnek 2: Varyant Yok
```
Product: Generic Item (SKU: ITEM-001)
├─ NO VARIANTS
└─ Product images:
   ├─ Image 1 (seq=0) ← PRIMARY_IMAGE olur
   ├─ Image 2 (seq=1)
   └─ Image 3 (seq=2)
```

---

## 📝 Değiştirilen Dosyalar

1. ✅ `marketing/views.py`
   - `ProductEdit.form_valid()` - Satır 955-985
   - `instant_upload_file()` - Satır 1112-1127 (zaten vardı)
   - `instant_delete_file()` - Satır 1170-1201 (yeni eklendi)

2. 📄 `PRIMARY_IMAGE_AUTO_UPDATE.md` (Bu dosya)

---

## ✅ Test Checklist

- [ ] Product edit → Save → Primary doğru mu?
- [ ] Varyant ekle → Primary güncellendi mi?
- [ ] Varyant sil → Primary güncellendi mi?
- [ ] Instant upload (variant) → Primary güncellendi mi?
- [ ] Instant delete (variant image) → Primary güncellendi mi?
- [ ] Varyant yok → Product image primary mi?
- [ ] Hiç görsel yok → primary_image = None?

---

**Oluşturulma:** 2025-11-08  
**Durum:** ✅ Implemented  
**Version:** 1.0
