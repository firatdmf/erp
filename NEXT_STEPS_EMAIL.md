# Email Automation - Şu Ana Kadar Yapılanlar ve Sonraki Adımlar

## ✅ TAMAMLANAN (Adım 1)

### 1. Django App Oluşturuldu
- `email_automation` app'i oluşturuldu

### 2. Database Modelleri ✅
- `EmailAccount` - Gmail hesabı bağlantısı
- `EmailTemplate` - 6 email şablonu sistemi
- `EmailCampaign` - Her company için campaign takibi
- `SentEmail` - Gönderilen emailler
- `ReceivedEmail` - Gelen emailler (inbox)

### 3. Settings Yapıldı ✅
- `INSTALLED_APPS`'e email_automation eklendi
- Gmail OAuth ayarları eklendi (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, etc.)

### 4. Migrations Yapıldı ✅
```bash
✅ python manage.py makemigrations email_automation
✅ python manage.py migrate
```

### 5. Admin Panel ✅
- Tüm modeller Django admin'e kaydedildi
- Admin panelden görüntülenebilir ve yönetilebilir

## 🔧 SIRADA (Adım 2 - Gmail Connection Page)

### Yapılacaklar:

#### 1. URLs Yapısı Oluştur
**Dosya:** `email_automation/urls.py` (yeni)
- Dashboard route
- Gmail connection routes
- Inbox/Outbox routes

#### 2. İlk View: Gmail Connection Page
**Dosya:** `email_automation/views.py`
- `dashboard()` - Ana email dashboard
- `connect_gmail()` - Gmail bağlantısı başlat
- `oauth2callback()` - OAuth callback handle et
- `disconnect_gmail()` - Gmail bağlantısını kes

#### 3. Template Oluştur
**Dosya:** `email_automation/templates/email_automation/dashboard.html`

**İçerik:**
- Gmail bağlı mı değil mi göster
- Eğer bağlı değilse: "Connect Gmail" butonu
- Eğer bağlıysa: 
  - Bağlı email göster
  - Disconnect butonu
  - Campaign istatistikleri

#### 4. Sidebar Menüye Mail Ekle
**Dosya:** `erp/templates/base.html`
```html
<li class="nav-item">
  <a href="{% url 'email:dashboard' %}" class="nav-link">
    <i class="fa fa-envelope fa-2x"></i>
    <span class="link-text">Mail</span>
  </a>
</li>
```

#### 5. Main URLs'e Bağla
**Dosya:** `erp/urls.py`
```python
path('email/', include('email_automation.urls')),
```

## 📝 ÖNEMLİ NOTLAR

### Google Cloud Console'dan Almanız Gerekenler:
1. Google Cloud Console'a git: https://console.cloud.google.com
2. Projenize gidin
3. "APIs & Services" > "Credentials"
4. OAuth 2.0 Client IDs kısmından:
   - Client ID
   - Client Secret
5. Bu bilgileri `.env` dosyanıza ekleyin:
```
GMAIL_CLIENT_ID=your-client-id-here
GMAIL_CLIENT_SECRET=your-client-secret-here
```

### Redirect URI Eklemeyi Unutmayın:
Google Cloud Console'da OAuth credentials'a ekleyin:
```
http://localhost:8000/email/oauth2callback/
```

## 🎯 BUGÜNKÜ HEDEF (Adım 2)

1. ✅ Modeller hazır
2. ⏭️ ŞIMDI: Gmail connection page + sidebar menü
3. Sonraki: Email templates oluşturma
4. Sonraki: Campaign listesi görüntüleme
5. Sonraki: Otomatik email gönderme

## 📦 PIP PAKETLERI (Kurulması Gerekiyor)

Şu paketler gerekli (network sorunu vardı, manuel kurmanız gerekebilir):
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Eğer hata alıyorsanız, tek tek deneyin:
```bash
pip install google-auth
pip install google-auth-oauthlib  
pip install google-auth-httplib2
pip install google-api-python-client
```

## 🚀 HIZLI TEST

Admin panelden kontrol edin:
1. http://localhost:8000/admin/ 
2. Email automation bölümünde modelleri görebilmeniz lazım:
   - Email Accounts
   - Email Templates
   - Email Campaigns
   - Sent Emails
   - Received Emails

## SONRAKI KOMUT

Bir sonraki adımda şunları yapacağız:
1. `email_automation/urls.py` oluştur
2. `email_automation/views.py` - Gmail connection views
3. Template oluştur
4. Sidebar menü ekle

Devam edelim mi?
