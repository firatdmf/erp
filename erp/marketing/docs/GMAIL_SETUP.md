# Gmail OAuth Setup Guide

Bu dokuman, email automation sistemini Gmail ile bağlamak için gerekli adımları açıklar.

## Adım 1: Google Cloud Console'da Proje Oluşturma

1. [Google Cloud Console](https://console.cloud.google.com/) adresine gidin
2. Yeni bir proje oluşturun veya mevcut bir projeyi seçin
3. Proje adını seçin (örn: "ERP Email Automation")

## Adım 2: Gmail API'yi Etkinleştirme

1. Soldaki menüden **"APIs & Services"** > **"Library"** seçin
2. **"Gmail API"** arayın
3. Gmail API'yi seçip **"Enable"** butonuna tıklayın

## Adım 3: OAuth Consent Screen Yapılandırma

1. **"APIs & Services"** > **"OAuth consent screen"** gidin
2. User Type olarak **"External"** seçin (dahili kullanıcılar için "Internal" seçebilirsiniz)
3. **"Create"** butonuna tıklayın
4. Gerekli bilgileri doldurun:
   - **App name**: ERP Email Automation
   - **User support email**: Your email
   - **Developer contact information**: Your email
5. **"Save and Continue"** tıklayın
6. **Scopes** sayfasında **"Add or Remove Scopes"** tıklayın
7. Şu scope'ları ekleyin:
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.modify`
8. **"Save and Continue"** tıklayın
9. **Test users** sayfasında kullanacağınız Gmail adresini ekleyin
10. **"Save and Continue"** tıklayın

## Adım 4: OAuth Credentials Oluşturma

1. **"APIs & Services"** > **"Credentials"** gidin
2. **"Create Credentials"** > **"OAuth client ID"** seçin
3. Application type olarak **"Web application"** seçin
4. Name: "ERP Web Client"
5. **Authorized redirect URIs** kısmına ekleyin:
   ```
   http://localhost:8000/email/oauth2callback/
   ```
   
   Eğer production'da kullanacaksanız, domain'inizi de ekleyin:
   ```
   https://yourdomain.com/email/oauth2callback/
   ```

6. **"Create"** butonuna tıklayın
7. Client ID ve Client Secret değerlerini kopyalayın

## Adım 5: .env Dosyasını Yapılandırma

Projenizin `.env` dosyasına aşağıdaki değerleri ekleyin:

```env
# Gmail OAuth Settings
GMAIL_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret-here
GMAIL_REDIRECT_URI=http://localhost:8000/email/oauth2callback/
```

**Önemli**: Production ortamında `GMAIL_REDIRECT_URI` değerini gerçek domain'iniz ile değiştirin.

## Adım 6: Gmail Hesabını Bağlama

1. Django sunucunuzu başlatın: `python manage.py runserver`
2. ERP sisteminize login olun
3. Sol menüden **"Mail"** seçeneğine tıklayın
4. **"Connect Gmail Account"** butonuna tıklayın
5. Google OAuth ekranına yönlendirileceksiniz
6. Gmail hesabınızı seçin ve izinleri onaylayın
7. Başarılı olursa dashboard'a geri döneceksiniz ve Gmail bağlı görünecek

## Sorun Giderme

### "redirect_uri_mismatch" Hatası

Bu hata, Google Cloud Console'da kayıtlı redirect URI ile gönderdiğiniz URI'nin eşleşmemesi durumunda oluşur.

**Çözüm**:
1. Google Cloud Console > Credentials'a gidin
2. OAuth Client ID'nizi düzenleyin
3. Authorized redirect URIs listesine tam olarak aşağıdaki URI'yi ekleyin:
   ```
   http://localhost:8000/email/oauth2callback/
   ```
4. Değişiklikleri kaydedin ve tekrar deneyin

### "access_denied" Hatası

Kullanıcı OAuth ekranında izinleri reddetti.

**Çözüm**: Tekrar "Connect Gmail Account" butonuna tıklayın ve bu sefer izinleri onaylayın.

### "invalid_client" Hatası

Client ID veya Client Secret yanlış.

**Çözüm**:
1. `.env` dosyasındaki `GMAIL_CLIENT_ID` ve `GMAIL_CLIENT_SECRET` değerlerini kontrol edin
2. Google Cloud Console'dan doğru değerleri kopyalayın
3. Django sunucusunu restart edin

### "OAuth is not configured" Mesajı

`.env` dosyasında Gmail OAuth ayarları eksik.

**Çözüm**:
1. `.env` dosyasına yukarıdaki Adım 5'teki ayarları ekleyin
2. Django sunucusunu restart edin

## Test Kullanıcıları

OAuth consent screen'i "Testing" modundayken, sadece Test Users listesine eklediğiniz Gmail hesapları ile bağlanabilirsiniz.

**Production'a Geçiş**:
1. Google Cloud Console > OAuth consent screen gidin
2. **"Publish App"** butonuna tıklayın
3. Onay sürecinden geçtikten sonra herkes uygulamanızı kullanabilir

## Güvenlik Notları

1. **Client Secret'ı asla paylaşmayın** veya public repository'lere push etmeyin
2. `.env` dosyası `.gitignore`'da olmalı
3. Production ortamında HTTPS kullanın
4. Sadece gerekli Gmail scope'larını isteyin

## API Limitleri

Gmail API'nin günlük kullanım limitleri vardır:
- **Günlük kullanım**: 1 milyar quota unit
- **Email gönderme**: Günde ~100-500 email (hesap tipine göre değişir)
- **Rate limit**: Saniyede 250 quota unit

Daha fazla bilgi için: [Gmail API Usage Limits](https://developers.google.com/gmail/api/reference/quota)

---

**Setup tamamlandı!** Artık Gmail hesabınızı bağlayabilir ve email automation kullanmaya başlayabilirsiniz.
