# 🔧 Email Otomasyon Sistemi - Sorun Giderme

## ❌ **SORUN: Checkbox işaretlemediğim halde email gidiyor!**

### Neden Oluyor?

Email sistemi **iki aşamalı** çalışıyor:

1. **Aşama 1:** Company oluşturulduğunda (checkbox kontrolü ile)
   - ✅ Checkbox işaretliyse → `CompanyFollowUp` kaydı oluşturulur
   - ❌ Checkbox işaretli değilse → Hiçbir şey oluşturulmaz

2. **Aşama 2:** Cron job çalıştığında (`send_followup_emails` komutu)
   - **TÜM** mevcut `CompanyFollowUp` kayıtlarına email gönderir
   - Checkbox'u kontrol etmez (çünkü zaten kayıt oluşturulmuş)

### 🎯 **Çözüm: Mevcut Follow-Up Kayıtlarını Temizleyin**

---

## 🛠️ **Adım 1: Mevcut Durumu Kontrol Edin**

```bash
# Hangi company'lerin follow-up sisteminde olduğunu görmek için:
python erp/manage.py cleanup_unwanted_followups --dry-run
```

**Çıktı Örneği:**
```
📧 FOLLOW-UP CLEANUP TOOL
============================================================
📊 Total follow-ups: 15
   ✅ Active: 8
   ❌ Inactive: 7

❌ SHOULD BE DELETED (5):
  • Test Company ABC                       | NO_EMAIL        | Company has no email address
  • XYZ Ltd                                | NOT_PROSPECT    | Status is "qualified"
  • Sample Inc                             | NOT_PROSPECT    | Status is "qualified"

⚠️  FOR REVIEW (7):
  • Old Company                            | COMPLETED       | Completed sequence (5/5 emails)
  • Another Co                             | STOPPED         | Stopped: status_changed

✅ LOOKS GOOD (3):
  • Real Prospect 1                        | ACTIVE          | Active - 2/5 emails sent
  • Real Prospect 2                        | ACTIVE          | Active - 0/5 emails sent

💡 TIP: Run without --dry-run to actually delete 5 records
```

---

## 🗑️ **Adım 2: İstenmeyen Kayıtları Silin**

```bash
# Gerçekten silmek için (dry-run olmadan):
python erp/manage.py cleanup_unwanted_followups
```

Bu komut otomatik olarak:
- ✅ Email adresi olmayan company'leri temizler
- ✅ Status'ü "prospect" olmayan company'leri temizler
- ✅ Inactive kayıtları gösterir (isteğe bağlı silebilirsiniz)

---

## 🎯 **Adım 3: Doğru Kullanım**

### ✅ Email Göndermek İstiyorsanız:

1. Company formunu açın
2. **"Send Follow-up Emails"** checkbox'ını **işaretleyin** ✓
3. Company'yi kaydedin
4. ✅ İlk email **hemen** gider
5. ✅ Kalan 4 email zamanında gider (3, 10, 24, 54. günlerde)

### ❌ Email Göndermek İstemiyorsanız:

1. Company formunu açın
2. **"Send Follow-up Emails"** checkbox'ını **BOŞ BIRAKIN** ☐
3. Company'yi kaydedin
4. ✅ Hiçbir email GİTMEZ
5. ✅ `CompanyFollowUp` kaydı OLUŞTURULMAZ

---

## 📊 **Admin Panelinden Kontrol**

### Follow-Up Kayıtlarını Görmek İçin:

1. Admin paneline girin: `/admin/`
2. **CRM → Company Follow Ups** sayfasına gidin
3. Hangi company'lerin sistemde olduğunu görün

### Filtreler:
- **Is active:** Sadece aktif follow-up'ları göster
- **Stopped reason:** Neden durduğunu görün
- **Emails sent count:** Kaç email gönderildiğini görün

### Manuel Durdurma:

1. İstemediğiniz bir follow-up bulun
2. Düzenle'ye tıklayın
3. **"Is active"** checkbox'ını kaldırın
4. **"Stopped reason"** yazın (örn: "manual_stop")
5. Kaydedin

---

## 🔍 **Logları Kontrol Etme**

### Company oluştururken ne olduğunu görmek için:

```bash
# Django server çalışırken terminal'e bakın:
python erp/manage.py runserver
```

**Checkbox İŞARETLİ ise:**
```
INFO: Follow-up emails ENABLED for Test Company - Creating follow-up tracking
INFO: Sending initial email to Test Company (test@example.com)
INFO: ✓ Initial email sent successfully to Test Company
```

**Checkbox BOŞ ise:**
```
INFO: Follow-up emails DISABLED for Test Company - Checkbox not checked
```

---

## 🚨 **Acil Durum: Tüm Email'leri Durdur**

### Eğer yanlışlıkla çok fazla follow-up oluşturulmuşsa:

```bash
# 1. Önce durumu kontrol et
python erp/manage.py cleanup_unwanted_followups --dry-run

# 2. Tümünü sil (dikkatli kullanın!)
python erp/manage.py cleanup_unwanted_followups
```

### Veya Manuel:

```bash
python erp/manage.py shell
```

```python
from crm.models import CompanyFollowUp

# TÜM aktif follow-up'ları durdur
CompanyFollowUp.objects.filter(is_active=True).update(
    is_active=False, 
    stopped_reason='manual_bulk_stop'
)

print("✓ Tüm aktif follow-up'lar durduruldu")
exit()
```

---

## 📋 **Özet: Email Ne Zaman Gönderilir?**

### ✅ Email GÖNDERİLİR:
1. Company oluşturulurken **checkbox işaretliyse** ✓
2. Status = **"prospect"** ise
3. Company'nin **email adresi varsa**
4. Cron job çalıştığında (günlük)

### ❌ Email GÖNDERİLMEZ:
1. Company oluşturulurken **checkbox boşsa** ☐
2. `CompanyFollowUp` kaydı **yoksa**
3. Follow-up **"is_active=False"** ise
4. Status **"prospect" değilse**
5. Email adresi **yoksa**

---

## 🔧 **Sık Sorulan Sorular**

### S1: Eski bir company'yi sisteme almak istersem?

**C:** Admin panelinden manuel olarak `CompanyFollowUp` oluşturun:
1. `/admin/crm/companyfollowup/add/` adresine gidin
2. Company'yi seçin
3. "Is active" işaretleyin
4. Kaydedin
5. Cron job çalıştığında email gönderilir

### S2: Bir company'yi geçici olarak durdurmak istersem?

**C:** Admin panelinden:
1. Follow-up kaydını bulun
2. "Is active" checkbox'ını kaldırın
3. "Stopped reason" = "temporary_pause" yazın
4. Kaydedin

### S3: Checkbox nereden geldi, ben görmedim?

**C:** Form'da "Send Follow-up Emails" adıyla var. Eğer göremiyorsanız:
```bash
# Template'i kontrol edin:
cat erp/crm/templates/crm/create_form.html | grep -i "followup"
```

### S4: Cron job nerede?

**C:** Cron job'u kendiniz ayarlamanız gerekir:
```bash
crontab -e

# Bu satırı ekleyin (her gün saat 9'da):
0 9 * * * cd /path/to/erp && python manage.py send_followup_emails
```

---

## ✅ **Kontrol Listesi**

Test etmek için:

- [ ] Yeni company oluştur (checkbox BOŞ) → Email GİTMEMELİ
- [ ] Yeni company oluştur (checkbox İŞARETLİ) → Email GÖNDERİLMELİ
- [ ] `cleanup_unwanted_followups --dry-run` çalıştır → Durumu gör
- [ ] Admin panelinde follow-up kayıtlarını kontrol et
- [ ] Logları kontrol et (terminal çıktısı)

---

## 📞 **Hala Sorun mu Var?**

1. Logları kontrol edin (yukardaki komutlar)
2. Admin panelinde `CompanyFollowUp` kayıtlarını kontrol edin
3. Cleanup command'ı çalıştırın
4. Cron job'u kontrol edin (`crontab -l`)

---

**Oluşturulma:** 2025-12-11  
**Versiyon:** 1.0  
**Durum:** ✅ Sorun çözüldü
