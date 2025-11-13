# Unsaved Changes Warning System

## Genel Bakış

Bu özellik, sidebar form'larında veri girilirken yanlışlıkla formu kapatmayı engeller. Kullanıcı formu doldurup henüz kaydetmeden boşluğa tıklayarak sidebar'ı kapatmaya çalışırsa, bir uyarı modal'ı gösterilir.

## Özellikler

✅ **Otomatik Algılama** - Formdaki herhangi bir değişiklik otomatik olarak algılanır
✅ **Modal Uyarı** - Kullanıcıya "unsaved changes" uyarısı gösterilir
✅ **Geri Dönüş** - Kullanıcı "Return to form" ile forma geri dönebilir
✅ **Discard** - Kullanıcı değişiklikleri atmayı onaylarsa form kapanır
✅ **Form Submit** - Form gönderildiğinde uyarı gösterilmez
✅ **Escape Tuşu** - ESC tuşuna basıldığında da aynı kontrol yapılır

## Desteklenen Form'lar

1. **Task Sidebar** (`#taskForm`)
2. **Company Sidebar** (`#companyForm`)
3. **Main Contact Sidebar** (`#mainContactForm`)

## Teknik Detaylar

### Dosyalar

#### 1. `static/erp/js/unsaved_changes_handler.js`
Ana JavaScript dosyası. Şu fonksiyonları içerir:

- `initializeFormTracking(formId)` - Form tracking'i başlatır
- `resetFormTracking()` - Tracking'i sıfırlar
- `showUnsavedChangesModal(onDiscard, onReturn)` - Uyarı modal'ını gösterir
- `wrapCloseFunctionWithCheck(originalFunction, formId)` - Close fonksiyonunu wrap eder

#### 2. `templates/base.html`
- Script import edildi
- Sidebar açma fonksiyonları `initializeFormTracking()` çağrısı ekli
- Close fonksiyonları unsaved changes check'i ile wrap edildi
- Submit fonksiyonlarında `setSubmitting()` flag'i set ediliyor

### Nasıl Çalışır?

1. **Form Açılışı**:
   ```javascript
   function openTaskSidebar() {
     // ... sidebar'ı aç
     initializeFormTracking('taskForm'); // Tracking başlat
   }
   ```

2. **Kullanıcı Form'u Doldurur**:
   - Her `input`, `textarea`, `select` değişikliği dinlenir
   - Değişiklik olduğunda `formHasChanges = true` olur

3. **Form Kapatma Denemesi**:
   ```javascript
   const closeTaskSidebar = function() {
     if (formChangeTracker.hasChanges()) {
       showUnsavedChangesModal(
         () => _closeTaskSidebarOriginal(), // Discard
         () => {} // Return to form
       );
     } else {
       _closeTaskSidebarOriginal();
     }
   };
   ```

4. **Modal Gösterimi**:
   - Sarı uyarı ikonu
   - "You have unsaved data!" başlığı
   - İki buton: "Return to the form" (mavi) ve "Discard changes" (gri)

5. **Form Submit**:
   ```javascript
   function submitCompanyForm(event) {
     formChangeTracker.setSubmitting(); // Submit flag
     // ... form gönder
   }
   ```
   - Submit olduğunda `isSubmitting = true` yapılır
   - Close çağrıldığında uyarı gösterilmez

### Modal Tasarımı

```
┌─────────────────────────────────────┐
│                                     │
│        ⚠️  (Sarı warning icon)      │
│                                     │
│    You have unsaved data!           │
│                                     │
│  The form you just closed had       │
│  unsaved changes. Are you sure      │
│  you want to close the form and     │
│  discard the changes?               │
│                                     │
│  [Return to the form] [Discard]     │
│     (Mavi buton)      (Gri buton)   │
└─────────────────────────────────────┘
```

## Kullanım Senaryoları

### Senaryo 1: Değişiklik Yapıldı, Overlay'e Tıklandı
1. Kullanıcı "Add Company" butonuna tıklar
2. Sidebar açılır
3. Kullanıcı company name girer
4. Kullanıcı yanlışlıkla boşluğa (overlay'e) tıklar
5. ✅ **Modal gösterilir**: "You have unsaved data!"
6. Kullanıcı "Return to form" seçer
7. ✅ **Sidebar açık kalır**, veriler kaybolmaz

### Senaryo 2: Değişiklik Yapıldı, Close Butonuna Tıklandı
1. Kullanıcı formu doldurur
2. Kullanıcı sağ üst köşedeki "X Close" butonuna tıklar
3. ✅ **Modal gösterilir**
4. Kullanıcı "Discard changes" seçer
5. ✅ **Sidebar kapanır**

### Senaryo 3: Değişiklik Yapılmadı
1. Kullanıcı sidebar'ı açar
2. Hiçbir şey yazmaz
3. Overlay'e tıklar
4. ✅ **Modal gösterilmez**, sidebar direkt kapanır

### Senaryo 4: Form Submit Edildi
1. Kullanıcı formu doldurur
2. "Create Company" butonuna tıklar
3. Form gönderilir
4. Sidebar kapanır
5. ✅ **Modal gösterilmez** (çünkü submit edildi)

## Gelecek İyileştirmeler

- [ ] Product sidebar'a da eklenebilir
- [ ] Edit form'larına da eklenebilir
- [ ] Local storage'a auto-save özelliği
- [ ] "Save as draft" özelliği
- [ ] Farklı diller için çeviri desteği

## Testing

### Manuel Test Adımları

1. **Task Form Test**:
   ```
   - Add > Task tıkla
   - Task name yaz
   - Boşluğa tıkla
   - Modal'ın göründüğünü doğrula
   - "Return to form" tıkla
   - Task name'in hala orada olduğunu doğrula
   ```

2. **Company Form Test**:
   ```
   - Add > Company tıkla
   - Company name yaz
   - ESC tuşuna bas
   - Modal'ın göründüğünü doğrula
   - "Discard" tıkla
   - Sidebar'ın kapandığını doğrula
   ```

3. **Submit Test**:
   ```
   - Add > Contact tıkla
   - Name ve email gir
   - "Add Contact" butonuna tıkla
   - Modal gösterilmediğini doğrula
   - Form'un gönderildiğini doğrula
   ```

## Browser Uyumluluğu

✅ Chrome 90+
✅ Firefox 88+
✅ Safari 14+
✅ Edge 90+

## Performans

- Minimal overhead (~2KB gzipped)
- Event listener'lar sadece form açıkken aktif
- Modal DOM'a lazily eklenir (sadece gerektiğinde)
- Animasyonlar CSS ile yapılır (60 FPS)

## Troubleshooting

### Modal Gösterilmiyor
- Browser console'da hata var mı kontrol et
- `unsaved_changes_handler.js` dosyası yüklendi mi?
- `initializeFormTracking()` çağrıldı mı?

### Modal Her Zaman Gösteriliyor
- `resetFormTracking()` doğru çağrılıyor mu?
- Submit handler'da `setSubmitting()` var mı?

### Animasyon Çalışmıyor
- CSS animations browser'da destekleniyor mu?
- `@keyframes` tanımları var mı?

---

**Son Güncelleme**: 2025-11-13
**Versiyon**: 1.0.0
**Geliştirici**: Nejum ERP Team
