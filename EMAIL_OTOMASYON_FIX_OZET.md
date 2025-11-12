# 🔧 Email Otomasyon Sorunu - TAM ÇÖZÜM

## ❌ **Gerçek Sorun Neydi?**

Projenizde **2 AYRI EMAIL SİSTEMİ** varmış ve ikisi de aktifti!

1. **CRM modülü** - `CompanyFollowUp` (eski sistem)
2. **email_automation modülü** - `EmailCampaign` (yeni sistem) ← **Bu aktif olarak kullanılıyor**

**email_automation** modülündeki signal checkbox'a bakmıyordu ve **HER PROSPECT COMPANY İÇİN OTOMATİK CAMPAIGN** oluşturuyordu!

---

## ✅ **Yapılan Düzeltmeler**

### 1. **email_automation/signals.py** - Checkbox Kontrolü Eklendi
```python
# ÖNCESİ:
if created and instance.status == 'prospect':
    # Her prospect için otomatik campaign oluşturuyordu ❌

# SONRASI:
if not getattr(instance, '_enable_email_campaign', False):
    return  # Checkbox işaretli değilse hiçbir şey yapma ✅
```

### 2. **crm/views.py** - Flag Ekleme
```python
# Company kaydedilmeden ÖNCE flag set ediliyor:
send_emails = form.cleaned_data.get("send_followup_emails", False)
self.object._enable_email_campaign = send_emails  # ← Signal için flag

# Artık sadece checkbox işaretliyse campaign oluşturuluyor
```

### 3. **Cleanup Tools Oluşturuldu**
İki ayrı cleanup tool:
- `cleanup_email_campaigns` - email_automation kampanyalarını temizler
- `cleanup_unwanted_followups` - CRM follow-up'ları temizler (eski sistem)

---

## 🚀 **ŞİMDİ YAPMANIZ GEREKENLER**

### 1. **Mevcut İstenmeyen Kampanyaları Temizleyin**

```bash
cd C:\Users\enes3\erp
.\vir_env\Scripts\activate

# Önce durumu kontrol edin (dry-run):
python erp/manage.py cleanup_email_campaigns --dry-run

# Eğer silinecek kampanyalar varsa, silin:
python erp/manage.py cleanup_email_campaigns
```

**Çıktı şuna benzer olacak:**
```
📧 EMAIL CAMPAIGN CLEANUP TOOL
============================================================
📊 Total campaigns: 10
   ✅ Active: 6
   ❌ Inactive: 4

❌ SHOULD BE DELETED (5):
  • Test Company                           | NO_EMAIL        | Company has no email
  • XYZ Corp                               | NOT_PROSPECT    | Status: qualified
  ...
```

### 2. **Server'ı Restart Edin**

```bash
# Değişikliklerin yüklenmesi için server'ı restart edin:
python erp/manage.py runserver
```

### 3. **Test Edin**

#### Test 1: Checkbox BOŞ (Email GÖNDERİLMEMELİ)
1. Sol menüden Add → Company
2. Company bilgilerini doldurun
3. **"Send Follow-up Emails" checkbox'ını BOŞ BIRAKIN** ☐
4. Save

**Terminal'de görmeli:**
```
⊘ Skipping campaign creation for [Company Name] - Email automation not enabled
⊘ Email automation DISABLED for [Company Name] - Checkbox not checked
```

**Kontrol:**
```bash
# Admin paneline girin:
http://localhost:8000/admin/email_automation/emailcampaign/

# Yeni company için campaign OLMAMALI ✅
```

#### Test 2: Checkbox İŞARETLİ (Email GÖNDERİLMELİ)
1. Yeni company oluşturun
2. **"Send Follow-up Emails" checkbox'ını İŞARETLEYİN** ✓
3. Save

**Terminal'de görmeli:**
```
✓ Campaign created for [Company Name]
  Next email (2) scheduled for 2025-11-15 ...
✓ Email 1 sent to company@email.com for campaign XX
✓ Email 1 sent immediately to [Company Name]
```

**Kontrol:**
```bash
# Admin panelde campaign OLMALI ✅
http://localhost:8000/admin/email_automation/emailcampaign/
```

---

## 🔍 **Gmail Credentials Hatası**

Loglarınızda bu hatayı gördünüz:
```
Failed to send follow-up email 1 to company: (535, b'5.7.8 Username and Password not accepted...')
```

### Çözüm: Gmail App Password Kontrolü

1. **`.env` dosyasını kontrol edin:**
```bash
cat erp\.env | Select-String "EMAIL"
```

2. **Doğru format:**
```env
EMAIL_HOST_USER=youremail@gmail.com
EMAIL_HOST_PASSWORD=abcd efgh ijkl mnop  # 16 karakterli App Password
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
```

3. **Gmail App Password oluşturun (eğer yoksa):**
   - https://myaccount.google.com/security adresine gidin
   - 2-Step Verification açın
   - App passwords → Mail → Generate
   - 16 karakterli şifreyi kopyalayın
   - `.env` dosyasına ekleyin (boşluklarla birlikte)

4. **Test edin:**
```bash
python erp/manage.py shell
```
```python
from django.core.mail import send_mail
send_mail(
    'Test Email',
    'This is a test.',
    'youremail@gmail.com',
    ['youremail@gmail.com'],
    fail_silently=False,
)
# Eğer hata vermeden çıkarsa ✅ credentials doğru
```

---

## 📊 **Hangi Sistem Kullanılıyor?**

**Aktif Sistem: email_automation modülü**

| Özellik | email_automation | CRM (eski) |
|---------|------------------|------------|
| Model | `EmailCampaign` | `CompanyFollowUp` |
| Email Sayısı | 6 | 5 |
| Template | `EmailTemplate` (esnek) | Sabit template'ler |
| Admin | `/admin/email_automation/` | `/admin/crm/companyfollowup/` |
| Durum | ✅ Aktif | ⚠️ Kullanılmıyor (ama kod var) |

---

## 📋 **Özet: Email Ne Zaman Gönderilir?**

### ✅ Email GÖNDERİLİR:
1. Checkbox **İŞARETLİ** ✓
2. Status = **"prospect"**
3. Company'nin **email adresi VAR**
4. User'ın **EmailTemplate'leri VAR**
5. User'ın **EmailAccount'u VAR** (Gmail bağlantısı)

### ❌ Email GÖNDERİLMEZ:
1. Checkbox **BOŞ** ☐
2. Status **"prospect" değil**
3. Email adresi **YOK**
4. Template veya Account **KURULMADI**

---

## 🛠️ **Maintenance Komutları**

### Kampanya Durumunu Kontrol:
```bash
# email_automation kampanyaları:
python erp/manage.py cleanup_email_campaigns --dry-run

# CRM follow-up'ları (eski):
python erp/manage.py cleanup_unwanted_followups --dry-run
```

### Temizlik:
```bash
# İstenmeyen kampanyaları sil:
python erp/manage.py cleanup_email_campaigns

# İstenmeyen follow-up'ları sil:
python erp/manage.py cleanup_unwanted_followups
```

### Manuel Durdurma:
```bash
python erp/manage.py shell
```
```python
from email_automation.models import EmailCampaign

# Belirli bir company:
campaign = EmailCampaign.objects.get(company__name="Test Company")
campaign.status = 'paused'
campaign.save()

# Tüm aktif kampanyalar:
EmailCampaign.objects.filter(status='active').update(status='paused')
```

---

## 📁 **Değiştirilen Dosyalar**

### Modified:
1. ✅ `email_automation/signals.py` - Checkbox kontrolü eklendi
2. ✅ `crm/views.py` - Flag ekleme + gereksiz kod temizlendi

### Created:
1. ✅ `email_automation/management/commands/cleanup_email_campaigns.py`
2. ✅ `email_automation/management/commands/__init__.py`
3. ✅ `email_automation/management/__init__.py`
4. ✅ `EMAIL_OTOMASYON_FIX_OZET.md` (Bu dosya)

---

## ✅ **Test Checklist**

- [ ] Server restart edildi
- [ ] `cleanup_email_campaigns --dry-run` çalıştırıldı
- [ ] İstenmeyen kampanyalar temizlendi
- [ ] Yeni company (checkbox BOŞ) → Email GİTMEDİ
- [ ] Yeni company (checkbox İŞARETLİ) → Email GİTTİ
- [ ] Terminal logları kontrol edildi
- [ ] Admin panelde kampanya durumu kontrol edildi
- [ ] Gmail credentials test edildi

---

## 🎯 **Başarı Kriterleri**

✅ **Sorun çözüldü sayılır eğer:**

1. Checkbox BOŞ bırakıldığında:
   - Terminal: `⊘ Skipping campaign creation` yazıyor
   - Admin'de campaign yok
   - Email GİTMİYOR

2. Checkbox işaretlendiğinde:
   - Terminal: `✓ Campaign created` yazıyor
   - Admin'de campaign var
   - Email GİDİYOR

3. Gmail credentials doğru çalışıyor (hata yok)

---

## 🐛 **Hala Sorun Varsa**

1. **Logları detaylı inceleyin:**
```bash
python erp/manage.py runserver
# Terminal çıktısına bakın
```

2. **Database kontrol:**
```bash
python erp/manage.py shell
```
```python
from email_automation.models import EmailCampaign
from crm.models import Company

# Kaç campaign var?
print(f"Total campaigns: {EmailCampaign.objects.count()}")
print(f"Active campaigns: {EmailCampaign.objects.filter(status='active').count()}")

# Son oluşturulan company:
last_company = Company.objects.latest('created_at')
print(f"Last company: {last_company.name}")
print(f"Has campaign: {hasattr(last_company, 'email_campaign')}")
```

3. **Signal aktif mi kontrol:**
```bash
python erp/manage.py shell
```
```python
from django.db.models import signals
from crm.models import Company
from email_automation import signals as email_signals

# Signal'ler listelensin:
for receiver in signals.post_save.receivers:
    print(receiver)
```

---

**Son Güncelleme:** 2025-12-11  
**Durum:** ✅ Sorun çözüldü  
**Test:** Bekliyor
