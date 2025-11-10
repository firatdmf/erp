# Performance Optimization Plan - Product Update

## Problem
- Product update çok yavaş (>1.5 saniye)
- Cloudinary'ye resim yükleme kullanıcıyı bekletiyor
- Resim sırası değiştirme/silme de yavaş

## Çözüm: Asenkron İşlemler + Progress Bar

### 1. Resim Yükleme (Priority: HIGH)
**Durum:** Cloudinary upload senkron - kullanıcı bekliyor
**Çözüm:** Background task ile asenkron yükle

#### Adımlar:
1. **Celery + Redis kurulumu** (background tasks için)
   - `pip install celery redis`
   - `celery.py` config dosyası oluştur
   - Celery worker başlat

2. **Task oluştur** (`marketing/tasks.py`)
   ```python
   from celery import shared_task
   
   @shared_task
   def upload_product_images_async(product_id, files_data):
       # Cloudinary'ye yükle
       # Database'e kaydet
       # WebSocket ile progress gönder
   ```

3. **View değişikliği** (`views.py`)
   ```python
   # Form submit'te:
   # - Product'ı hemen kaydet
   # - Task'ı başlat (asenkron)
   # - Redirect et (1 saniye içinde)
   upload_product_images_async.delay(product.id, files)
   ```

4. **Progress Bar** (product_detail.html)
   - WebSocket bağlantısı (django-channels)
   - Circular progress bar göster
   - "Resimler yükleniyor: 2/5" yazısı

#### Alternatif (Basit, Celery'siz):
- JavaScript ile AJAX upload
- Chunk'lar halinde yükle (5 resim varsa 1'er 1'er)
- Frontend'de progress bar
- Backend hızlı response (resimler sonra)

---

### 2. Resim Sırası Değiştirme (Priority: MEDIUM)
**Durum:** Full page reload - yavaş
**Çözüm:** AJAX request

#### Adımlar:
1. **AJAX endpoint** (`urls.py`)
   ```python
   path('product/<int:pk>/reorder-images/', ReorderImagesView, name='reorder_images')
   ```

2. **View** (sadece order güncelle, redirect yok)
   ```python
   def reorder_images(request, pk):
       order = json.loads(request.POST.get('order'))
       # Update sequence in DB
       return JsonResponse({'success': True})
   ```

3. **Frontend** (drag-drop'tan sonra)
   ```javascript
   fetch('/marketing/product/123/reorder-images/', {
       method: 'POST',
       body: JSON.stringify({order: [4,2,3,1,5]})
   }).then(() => {
       // Toast mesajı: "Sıra güncellendi"
       // NO PAGE RELOAD
   });
   ```

---

### 3. Resim Silme (Priority: MEDIUM)
**Durum:** Full page reload
**Çözüm:** AJAX delete

#### Adımlar:
1. **AJAX endpoint**
   ```python
   path('product/file/<int:pk>/delete/', DeleteFileView, name='delete_file')
   ```

2. **View** (background'da Cloudinary'den sil)
   ```python
   def delete_file(request, pk):
       file = ProductFile.objects.get(pk=pk)
       # Celery task ile Cloudinary'den sil (asenkron)
       file.delete()  # DB'den hemen sil
       return JsonResponse({'success': True})
   ```

3. **Frontend**
   ```javascript
   // Delete butonuna tıklayınca:
   fetch('/marketing/product/file/456/delete/', {method: 'DELETE'})
   .then(() => {
       // Resmi DOM'dan kaldır (fade out animasyon)
       imageElement.remove();
   });
   ```

---

### 4. Variant İşlemleri (Priority: LOW)
**Durum:** Variant save yavaş
**Çözüm:** Bulk insert + transaction optimization

#### Adımlar:
1. **Bulk create kullan**
   ```python
   # Şu anki: 
   for variant in variants:
       variant.save()  # N query
   
   # Optimize:
   ProductVariant.objects.bulk_create(variants)  # 1 query
   ```

2. **Transaction azalt**
   - Gereksiz `save()` çağrılarını kaldır
   - Sadece değişen alanları update et

---

## Implementasyon Sırası

### Haftaya 1 (Hızlı Kazanımlar)
- [ ] Resim sırası değiştirme → AJAX
- [ ] Resim silme → AJAX
- [ ] Toast notification sistemi ekle

### Haftaya 2 (Asenkron Upload)
- [ ] Celery + Redis kurulum
- [ ] Background task için `upload_product_images_async`
- [ ] WebSocket ile progress tracking

### Haftaya 3 (Polish)
- [ ] Progress bar animasyonları
- [ ] Error handling (upload fail olursa)
- [ ] Retry mechanism

---

## Beklenen Sonuçlar

| İşlem | Şimdi | Sonra |
|-------|-------|-------|
| Resim yükleme (5 resim) | 8 saniye | <1 saniye (async) |
| Resim sırası değiştir | 1.3 saniye | <200ms (AJAX) |
| Resim sil | 1.3 saniye | <200ms (AJAX) |
| Variant ekle/güncelle | 2 saniye | <800ms (bulk) |

---

## Teknoloji Stack

### Şu An
- Django sync views
- Full page reload
- Senkron Cloudinary upload

### Sonra
- Django + Celery (background tasks)
- Redis (message broker)
- AJAX (partial updates)
- WebSocket veya Polling (progress tracking)
- django-channels (opsiyonel, WebSocket için)

---

## Alternatif: Cloudinary'siz
Eğer Cloudinary yavaşsa:
1. **Local storage** (geçici) → S3'e background'da transfer
2. **Direct upload** - Client'tan Cloudinary'ye direkt (Django'yu bypass)
3. **Signed upload URL** - Güvenli ama hızlı

---

## Not
- Redis için: **Upstash** (ücretsiz tier, 10K request/gün)
- Celery için: 1 worker yeterli (development)
- Production'da: 2-3 worker + monitoring
