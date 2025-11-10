# Instant File Upload/Delete - Implementation Guide

## ✅ Tamamlanan

### Backend
1. ✅ `instant_upload_file` endpoint - `/marketing/api/instant_upload_file/`
2. ✅ `instant_delete_file` endpoint - `/marketing/api/instant_delete_file/`
3. ✅ URL routing eklendi

### Frontend
1. ✅ `instant_file_manager.js` oluşturuldu
2. ✅ Toast notifications
3. ✅ Progress bar
4. ✅ Instant preview
5. ✅ Instant delete

---

## 🎯 Nasıl Kullanılır?

### 1. Template'e JavaScript Dosyasını Ekle

**`product_form.html`** veya **`product_edit.html`** template'inin sonuna ekle:

```html
{% block javascript %}
{{ block.super }}
<script src="{% static 'marketing/js/instant_file_manager.js' %}"></script>

<script>
// Product ID'yi al (Django template variable)
const productId = {{ product.id }};

// File input için handler ekle
document.getElementById('your-file-input-id').addEventListener('change', async function(e) {
    const files = e.target.files;
    const container = document.getElementById('preview-container');
    
    for (let file of files) {
        await instantUploadFile(file, productId, null, container);
    }
    
    // Input'u temizle (aynı dosyayı tekrar seçebilmek için)
    this.value = '';
});
</script>
{% endblock %}
```

---

## 📝 Template Örnekleri

### Örnek 1: Basit File Upload

```html
<div class="upload-section">
    <h3>Ürün Resimleri</h3>
    
    <!-- File Input -->
    <input type="file" id="product-images" multiple accept="image/*">
    
    <!-- Preview Container -->
    <div id="image-preview-container" style="display: flex; flex-wrap: wrap;"></div>
</div>

<script>
const productId = {{ product.id }};

document.getElementById('product-images').addEventListener('change', async function(e) {
    const files = e.target.files;
    const container = document.getElementById('image-preview-container');
    
    for (let file of files) {
        await instantUploadFile(file, productId, null, container);
    }
    
    this.value = '';
});
</script>
```

### Örnek 2: Drag & Drop Upload

```html
<div id="drop-zone" style="
    border: 2px dashed #3b82f6;
    border-radius: 8px;
    padding: 40px;
    text-align: center;
    cursor: pointer;
">
    <p>📤 Resimleri buraya sürükleyin veya tıklayın</p>
    <input type="file" id="file-input" multiple accept="image/*" style="display: none;">
</div>

<div id="preview-container"></div>

<script>
const productId = {{ product.id }};
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const container = document.getElementById('preview-container');

// Click to select
dropZone.addEventListener('click', () => fileInput.click());

// File input change
fileInput.addEventListener('change', async function(e) {
    for (let file of e.target.files) {
        await instantUploadFile(file, productId, null, container);
    }
    this.value = '';
});

// Drag & Drop
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.background = '#dbeafe';
});

dropZone.addEventListener('dragleave', () => {
    dropZone.style.background = '';
});

dropZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropZone.style.background = '';
    
    const files = e.dataTransfer.files;
    for (let file of files) {
        if (file.type.startsWith('image/')) {
            await instantUploadFile(file, productId, null, container);
        }
    }
});
</script>
```

### Örnek 3: Variant Resimleri

```html
<div class="variant-images">
    <h4>Variant: {{ variant.variant_sku }}</h4>
    
    <input type="file" 
           id="variant-{{ variant.id }}-images" 
           data-variant-id="{{ variant.id }}"
           multiple 
           accept="image/*">
    
    <div id="variant-{{ variant.id }}-preview"></div>
</div>

<script>
const productId = {{ product.id }};

document.querySelectorAll('[id^="variant-"]').forEach(input => {
    input.addEventListener('change', async function(e) {
        const variantId = this.dataset.variantId;
        const container = document.getElementById(`variant-${variantId}-preview`);
        
        for (let file of e.target.files) {
            await instantUploadFile(file, productId, variantId, container);
        }
        
        this.value = '';
    });
});
</script>
```

---

## 🗑️ Mevcut Resimlere Delete Butonu Ekle

Eğer sayfada zaten yüklenmiş resimler varsa, onlara delete butonu eklemen gerekiyor:

```html
<div class="existing-images">
    {% for file in product.files.all %}
    <div class="file-preview-item" data-file-id="{{ file.id }}">
        <img src="{{ file.file_url }}" alt="Product image">
        <button type="button" 
                class="instant-delete-btn" 
                data-file-id="{{ file.id }}">×</button>
    </div>
    {% endfor %}
</div>
```

**Not:** `.instant-delete-btn` class'ı otomatik olarak tanınır ve işlenir (instant_file_manager.js'de).

---

## 🎨 CSS Özelleştirmesi

Varsayılan stiller inline olarak ekleniyor. Eğer kendi stilini kullanmak istersen:

```css
/* Custom styles */
.file-preview-item {
    position: relative;
    display: inline-block;
    margin: 10px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
    width: 200px; /* Customize */
    height: 200px;
}

.file-preview-item img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.instant-delete-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    background: #ef4444;
    color: white;
    border: none;
    border-radius: 50%;
    width: 32px;
    height: 32px;
    cursor: pointer;
}
```

---

## 🔧 API Referansı

### Upload Endpoint

**URL:** `POST /marketing/api/instant_upload_file/`

**Request:** `multipart/form-data`
```
file: <File>
product_id: <int>
variant_id: <int> (optional)
```

**Response:**
```json
{
    "success": true,
    "file": {
        "id": 123,
        "url": "https://cloudinary.com/...",
        "sequence": 0,
        "is_primary": false
    }
}
```

### Delete Endpoint

**URL:** `POST /marketing/api/instant_delete_file/`

**Request:** `application/json`
```json
{
    "file_id": 123
}
```

**Response:**
```json
{
    "success": true,
    "message": "File deleted successfully"
}
```

---

## ⚡ Özellikler

### 1. Progress Bar
Yükleme sırasında otomatik progress bar gösterir:
- 📤 Yükleniyor: filename.jpg
- Progress bar (30% → 60% → 100%)

### 2. Toast Notifications
- ✅ "Dosya yüklendi!" (yeşil)
- 🗑️ "Dosya silindi!" (yeşil)
- ❌ "Hata!" (kırmızı)

### 3. Instant Preview
Yüklenen resim hemen görünür, sayfa yenilenmez.

### 4. Confirmation
Silme işleminden önce "Emin misiniz?" sorusu.

### 5. Animation
- FadeIn animasyonu (upload)
- FadeOut animasyonu (delete)
- Smooth transitions

---

## 🐛 Troubleshooting

### Resim yüklenmiyor
1. CSRF token doğru mu? (Console'da hata var mı?)
2. URL doğru mu? `/marketing/api/instant_upload_file/`
3. `product_id` gönderiliyor mu?
4. Cloudinary credentials doğru mu?

### Silme çalışmıyor
1. `file_id` doğru gönderiliyor mu?
2. ProductFile.delete() metodu çalışıyor mu?
3. Console'da error var mı?

### Sayfa yenilenince resimler kaybolmuyor
Bu normal! Resimler DB'ye kaydediliyor, sayfa yenilenince mevcut resimler template'den gelir.

---

## 🚀 Sonraki Adımlar

### 1. Image Optimization Ekle (Faz 2)
- Yüklemeden önce sıkıştır
- AVIF/WebP formatına çevir
- Thumbnail oluştur

### 2. Bulk Upload
- Birden fazla resmi aynı anda yükle
- Toplam progress göster

### 3. Image Reordering
- Drag-drop ile sıralama
- AJAX ile sequence güncelle

---

## ✅ Test Checklist

- [ ] Tek resim yükleme çalışıyor
- [ ] Çoklu resim yükleme çalışıyor
- [ ] Progress bar görünüyor
- [ ] Instant preview çalışıyor
- [ ] Toast notification görünüyor
- [ ] Delete butonu çalışıyor
- [ ] Confirmation dialog açılıyor
- [ ] Sayfa yenilenince resimler kalıyor
- [ ] Variant resimleri ayrı yükleniyor
- [ ] Cloudinary'den gerçekten siliyor

---

**Created:** 2025-11-02  
**Status:** ✅ Ready to Use  
**Next:** Template'lere entegre et ve test et!
