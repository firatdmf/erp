# Nejum ERP - Proje Dokümantasyonu

## 📋 İçindekiler
- [Proje Genel Bakış](#proje-genel-bakış)
- [Teknoloji Stack](#teknoloji-stack)
- [Proje Yapısı](#proje-yapısı)
- [Backend Modülleri](#backend-modülleri)
  - [Accounting (Muhasebe)](#1-accounting-muhasebe)
  - [CRM (Müşteri İlişkileri Yönetimi)](#2-crm-müşteri-i̇lişkileri-yönetimi)
  - [Marketing (Pazarlama)](#3-marketing-pazarlama)
  - [Operating (Operasyonlar)](#4-operating-operasyonlar)
  - [Authentication (Kimlik Doğrulama)](#5-authentication-kimlik-doğrulama)
  - [Todo (Görev Yönetimi)](#6-todo-görev-yönetimi)
- [Veritabanı Yapısı](#veritabanı-yapısı)
- [Önemli Özellikler](#önemli-özellikler)
- [Kurulum ve Çalıştırma](#kurulum-ve-çalıştırma)

---

## Proje Genel Bakış

**Nejum ERP**, modern yazılım altyapısı olmayan üretim tesisleri için tasarlanmış hafif, modüler bir web tabanlı ERP sistemidir. Proje, üretim tesislerinin hızlıca ayağa kalkmasını ve operasyonlarını dijitalleştirmesini sağlamak amacıyla geliştirilmiştir.

### Temel Değerler
> **"We build small systems that give people big control over their work."**

### Misyon
En basit açık kaynaklı endüstriyel otomasyon sistemini oluşturmak.

---

## Teknoloji Stack

### Backend
- **Framework:** Django 4.2.4
- **Database:** PostgreSQL (production), SQLite (development)
- **ORM:** Django ORM
- **Authentication:** Django Auth + Custom Member System
- **API:** RESTful (planned)

### Frontend
- **Template Engine:** Django Templates
- **HTMX:** django-htmx (1.18.0) - Dynamic interactions
- **jQuery:** django-jquery (3.1.0)
- **Static Files:** WhiteNoise (6.8.2) - Compressed static file serving

### Medya ve Depolama
- **CDN:** Cloudinary (1.44.0)
- **Image Processing:** Pillow (11.3.0), pillow-avif-plugin (1.5.2)
- **File Storage:** django-cloudinary-storage (0.3.0)

### Veri İşleme ve Analiz
- **Excel:** openpyxl (3.1.5), pandas (2.2.3)
- **PDF Generation:** reportlab (4.4.3)
- **QR Code:** segno (1.6.6)
- **Currency Conversion:** CurrencyConverter (0.17.27), forex-python (1.9.2)

### Deployment
- **WSGI Server:** Gunicorn (20.1.0)
- **Environment:** python-decouple (3.8) - Configuration management
- **Platforms:** Vercel, Render

### Diğer Önemli Kütüphaneler
- **HTML Processing:** beautifulsoup4 (4.12.3), lxml (5.3.0), html5lib (1.1)
- **Code Formatting:** djlint (1.34.1)
- **HTTP Requests:** requests (2.31.0)
- **Security:** cryptography (41.0.4)

---

## Proje Yapısı

```
erp/
├── erp/                          # Ana Django projesi
│   ├── __init__.py
│   ├── settings.py              # Proje ayarları
│   ├── urls.py                  # Ana URL yapılandırması
│   ├── views.py                 # Genel view'lar (Dashboard, Index, Reports)
│   ├── wsgi.py                  # WSGI yapılandırması
│   ├── asgi.py                  # ASGI yapılandırması
│   ├── context_processors.py   # Global template context
│   └── templates/               # Genel template'ler
│       ├── base.html
│       ├── index.html
│       ├── dashboard.html
│       └── reports.html
│
├── accounting/                   # Muhasebe Modülü
│   ├── models.py                # Finansal modeller (Book, CashAccount, vb.)
│   ├── views.py                 # Muhasebe view'ları
│   ├── forms.py                 # Muhasebe formları
│   ├── admin.py                 # Admin panel yapılandırması
│   ├── services.py              # İş mantığı servisleri
│   ├── signals.py               # Django signals
│   ├── urls.py                  # URL routing
│   ├── migrations/              # Veritabanı migration'ları
│   ├── templates/               # Muhasebe template'leri
│   └── static/                  # Modül özel static dosyalar
│
├── crm/                          # CRM Modülü
│   ├── models.py                # CRM modelleri (Contact, Company, Supplier)
│   ├── views.py                 # CRM view'ları
│   ├── forms.py
│   ├── admin.py
│   ├── urls.py
│   ├── signals.py               # Follow-up email automation
│   ├── management/              # Custom Django komutları
│   │   └── commands/
│   │       └── send_followup_emails.py
│   ├── migrations/
│   ├── templates/
│   └── static/
│
├── marketing/                    # Pazarlama Modülü
│   ├── models.py                # Ürün modelleri (Product, ProductVariant)
│   ├── views.py                 # Ürün yönetimi view'ları
│   ├── forms.py
│   ├── admin.py
│   ├── urls.py
│   ├── signals.py               # Cloudinary entegrasyonu
│   ├── migrations/
│   ├── templates/
│   └── static/
│
├── operating/                    # Operasyon Modülü
│   ├── models.py                # Operasyonel modeller (Order, RawMaterial)
│   ├── views.py                 # Sipariş yönetimi
│   ├── forms.py
│   ├── admin.py
│   ├── urls.py
│   ├── migrations/
│   ├── templates/
│   └── static/
│
├── authentication/               # Kimlik Doğrulama
│   ├── models.py                # Member, Permission modelleri
│   ├── views.py                 # Login, signup, logout
│   ├── forms.py
│   ├── admin.py
│   ├── urls.py
│   ├── migrations/
│   ├── templates/
│   └── static/
│
├── todo/                         # Görev Yönetimi
│   ├── models.py                # Task modeli
│   ├── views.py
│   ├── forms.py
│   ├── admin.py
│   ├── urls.py
│   ├── migrations/
│   ├── templates/
│   └── static/
│
├── product_files/                # Ürün medya dosyaları (local)
├── static/                       # Collected static files
├── media/                        # User uploaded media
├── manage.py                     # Django yönetim betiği
├── requirements.txt              # Python bağımlılıkları
├── .env                          # Environment variables (gitignore'da)
├── db.sqlite3                    # Development veritabanı
└── README.md                     # Proje dokümantasyonu
```

---

## Backend Modülleri

### 1. Accounting (Muhasebe)

**Amaç:** Tüm finansal işlemleri yönetmek, nakit akışını takip etmek, envanter muhasebesi yapmak.

#### Ana Modeller:

##### 1.1 Book (Defter)
- **Açıklama:** İşletmenin farklı bölümlerini veya projelerini ayrı defterlerde tutmak için kullanılır.
- **Özellikler:**
  - `name`: Defter adı (örn: "Ana Şirket", "Proje X")
  - `total_shares`: Toplam hisse sayısı (10,000,000 default)
  - `stakeholders`: İlişkili paydaşlar

##### 1.2 StakeholderBook
- **Açıklama:** Bir defterdeki paydaşların sahiplik paylarını tutar.
- **İlişki:** Member ↔ Book

##### 1.3 CurrencyCategory
- **Açıklama:** Desteklenen para birimlerini tanımlar.
- **Özellikler:**
  - `code`: Para birimi kodu (USD, EUR, TRY)
  - `name`: Para birimi adı
  - `symbol`: Para birimi sembolü ($, €, ₺)

##### 1.4 CurrencyExchangeRate
- **Açıklama:** Günlük döviz kurlarını saklar.
- **Otomatik Güncelleme:** services.py'de tanımlı

##### 1.5 CashAccount (Kasa/Banka Hesabı)
- **Açıklama:** Tüm nakit hesaplarını temsil eder.
- **Özellikler:**
  - `book`: Hangi deftere ait
  - `name`: Hesap adı (örn: "Ziraat Bankası TRY")
  - `currency`: Para birimi
  - `balance`: Güncel bakiye
- **Constraint:** Her defter için (name + currency) unique

##### 1.6 Equity Modelleri
- **EquityCapital:** Sermaye yatırımları
  - Paydaş sermaye katkıları
  - Yeni hisse ihracı
- **EquityRevenue:** Gelirler
  - Satış gelirleri (Order ile ilişkili)
  - Diğer gelirler (iade, bonus vb.)
- **EquityExpense:** Giderler
  - Kategorize edilmiş giderler
  - ExpenseCategory ile ilişkili
- **EquityDivident:** Kar payları
  - Paydaşlara dağıtılan temettüler

##### 1.7 Asset Modelleri
- **AssetCash:** Nakit varlıklar (deprecated - CashAccount kullanılıyor)
- **AssetInventoryRawMaterial:** Hammadde envanteri
  - operating.RawMaterialGood ile ilişkili
  - FIFO/Average maliyet hesaplama
- **AssetInventoryFinishedGood:** Bitmiş ürün envanteri
  - Durum: WIP (Work in Progress) / Finished
  - Depo ve lokasyon takibi
- **AssetAccountsReceivable:** Alacak hesapları
  - Contact, Company veya Supplier'dan alacaklar
  - Ödeme durumu takibi

##### 1.8 Liability Modelleri
- **LiabilityAccountsPayable:** Borç hesapları
  - Tedarikçilere olan borçlar
  - Hammadde veya bitmiş ürün alımları
  - Ödeme durumu takibi

##### 1.9 Transfer Modelleri
- **InTransfer:** Aynı para birimi hesaplar arası transfer
- **CurrencyExchange:** Farklı para birimleri arası dönüşüm

##### 1.10 CashTransactionEntry
- **Açıklama:** Tüm nakit işlemlerinin günlüğü (audit trail)
- **Özellikler:**
  - Generic Foreign Key ile herhangi bir finansal modele bağlanabilir
  - Otomatik bakiye hesaplama
  - Para birimi dönüşümleri
  - Running balance (kümülatif bakiye)

##### 1.11 Goods Receipt Modelleri
- **FinishedGoodsReceipt:** Bitmiş ürün alım fişi
- **FinishedGoodsReceiptItem:** Alım fişi kalemleri

#### Önemli Özellikler:
- **Multi-Currency Support:** Çoklu para birimi desteği
- **Automatic Exchange Rates:** Otomatik döviz kuru güncellemesi
- **Running Balance Calculation:** Her işlemde güncel bakiye hesaplama
- **Audit Trail:** Tüm işlemler CashTransactionEntry'de loglanır
- **Generic Relations:** ContentType kullanarak esnek işlem kayıtları

---

### 2. CRM (Müşteri İlişkileri Yönetimi)

**Amaç:** Müşteriler, şirketler, tedarikçiler ve iletişim takibi.

#### Ana Modeller:

##### 2.1 ClientGroup
- **Açıklama:** Müşteri segmentasyonu (örn: "tech", "manufacturing")
- **Kullanım:** Company ve Contact'larda kullanılır

##### 2.2 Company (Şirket)
- **Açıklama:** Kurumsal müşteriler
- **Özellikler:**
  - İletişim bilgileri (email, phone, website, address)
  - Background info (geçmiş notlar)
  - `status`: "prospect" veya "qualified"
  - `group`: ClientGroup ile ilişki
- **İlişkiler:**
  - Contact'lar (bir şirketin birden fazla irtibat kişisi olabilir)
  - Note'lar
  - Task'lar
  - AccountsReceivable

##### 2.3 Contact (İrtibat Kişisi)
- **Açıklama:** Bireysel müşteriler veya şirket çalışanları
- **Özellikler:**
  - Kişisel bilgiler (name, job_title, birthday)
  - Company ile opsiyonel ilişki
  - Group classification
- **İlişkiler:**
  - Company (opsiyonel)
  - Note'lar
  - Task'lar
  - AccountsReceivable

##### 2.4 Supplier (Tedarikçi)
- **Açıklama:** Hammadde veya bitmiş ürün tedarikçileri
- **Özellikler:**
  - `company_name` veya `contact_name` (en az biri zorunlu)
  - İletişim bilgileri
- **İlişkiler:**
  - Product (marketing.Product)
  - RawMaterialGoodReceipt (operating)
  - AccountsPayable (accounting)

##### 2.5 Note
- **Açıklama:** Contact veya Company için notlar
- **Özellikler:**
  - `content`: Not içeriği
  - `created_at`, `modified_date`: Zaman damgaları
- **İlişki:** Contact veya Company (biri zorunlu)

##### 2.6 CompanyFollowUp
- **Açıklama:** Otomatik takip e-postaları sistemi (prospect şirketler için)
- **Follow-up Schedule:**
  - Email 1: Şirket oluşturulduğunda hemen
  - Email 2: İlk emailden 3 gün sonra
  - Email 3: 2. emailden 7 gün sonra (toplam 10 gün)
  - Email 4: 3. emailden 14 gün sonra (toplam 24 gün)
  - Email 5: 4. emailden 30 gün sonra (toplam 54 gün)
- **Özellikler:**
  - `is_active`: Aktif/pasif durum
  - `emails_sent_count`: Gönderilen email sayısı
  - `stopped_reason`: Durdurulma nedeni
  - `last_email_sent_at`: Son email tarihi
- **Otomasyon:** 
  - `management/commands/send_followup_emails.py` komutu ile
  - Cron job ile günlük çalıştırılmalı
- **Durdurma Koşulları:**
  - Status "qualified" olursa
  - 5 email gönderildiyse
  - Manuel durdurulursa

#### Signals:
- **post_save (Company):** Yeni prospect şirket için CompanyFollowUp oluşturur ve ilk emaili gönderir
- **post_save (Company - status change):** Status "qualified" olursa follow-up'ı durdurur

---

### 3. Marketing (Pazarlama)

**Amaç:** Ürün kataloğu yönetimi, varyant sistemi, medya dosyaları.

#### Ana Modeller:

##### 3.1 ProductCategory
- **Açıklama:** Ürün kategorileri (standardize)
- **Özellikler:**
  - `name`: Kategori adı (unique, lowercase, underscore)
  - `description`: Açıklama
  - `image_url`: Cloudinary URL
- **Cloudinary Entegrasyonu:** save() metodunda otomatik upload

##### 3.2 ProductCollection
- **Açıklama:** Ürün koleksiyonları (manuel gruplar)
- **Kullanım:** Sezonluk koleksiyonlar, kampanyalar vb.

##### 3.3 Product (Ana Ürün)
- **Açıklama:** Sisteme kayıtlı tüm ürünler
- **Temel Bilgiler:**
  - `title`: Ürün başlığı
  - `description`: HTML destekli açıklama
  - `sku`: Stock Keeping Unit (unique)
  - `barcode`: Barkod (ISBN, UPC, GTIN)
- **Kategorizasyon:**
  - `category`: ProductCategory (standardize)
  - `type`: Custom type (serbest metin)
  - `collections`: ManyToMany ProductCollection
  - `tags`: PostgreSQL ArrayField (etiketler)
- **Stok ve Fiyat:**
  - `quantity`: Stok miktarı
  - `minimum_inventory_level`: Minimum stok seviyesi
  - `unit_of_measurement`: "units", "mt", "kg"
  - `price`: Satış fiyatı
- **Fiziksel Özellikler:**
  - `weight`: Ağırlık
  - `unit_of_weight`: "lb", "oz", "kg", "g"
- **Görünürlük:**
  - `featured`: Pazarlama kanallarında göster (Boolean)
  - `selling_while_out_of_stock`: Stok yokken sat
- **İlişkiler:**
  - `supplier`: Tedarikçi (crm.Supplier)
  - `primary_image`: ProductFile (vitrin görseli)
- **Dosyalar:**
  - `datasheet_url`: Teknik doküman URL

##### 3.4 ProductVariant
- **Açıklama:** Ürün varyantları (renk, beden, model vb.)
- **Özellikler:**
  - `product`: Ana ürün (ForeignKey)
  - `variant_sku`: Varyant SKU (unique değil)
  - `variant_barcode`: Varyant barkodu
  - `variant_quantity`: Varyant stok miktarı
  - `variant_price`: Varyant fiyatı
  - `variant_cost`: Varyant maliyet
  - `variant_featured`: Görünürlük
  - `product_variant_attribute_values`: ManyToMany (varyant özellikleri)

##### 3.5 ProductVariantAttribute
- **Açıklama:** Varyant özellik tipleri (örn: "color", "size", "material")
- **Özellikler:**
  - `name`: Özellik adı (unique, lowercase, no spaces)
- **Örnek:** "color", "size", "model"

##### 3.6 ProductVariantAttributeValue
- **Açıklama:** Varyant özellik değerleri
- **Özellikler:**
  - `product_variant_attribute`: Hangi özellik
  - `product_variant_attribute_value`: Değer (örn: "red", "xl", "2024")
- **Unique Constraint:** (attribute, value) çifti unique
- **Otomatik Format:** Lowercase + underscore

##### 3.7 ProductFile
- **Açıklama:** Ürün görselleri ve medya dosyaları
- **Özellikler:**
  - `file_url`: Cloudinary URL
  - `file_path`: Deprecated (local path)
  - `product`: Ana ürün (opsiyonel)
  - `product_variant`: Varyant (opsiyonel)
  - `is_primary`: Birincil görsel mi?
  - `sequence`: Sıralama
- **Cloudinary:**
  - Otomatik upload (signals.py)
  - Optimized URL generation (f_auto, q_auto)
  - Otomatik silme (delete metodunda)
- **Validasyon:**
  - File size: Max 10MB
  - File types: jpg, png, gif, webp, avif, mp4, hls, mp3

#### Önemli Özellikler:
- **Cloudinary CDN Integration:** Tüm medya dosyaları Cloudinary'de
- **Automatic Image Optimization:** URL'lerde otomatik format/quality
- **Variant System:** Esnek varyant özellik sistemi
- **Multi-Image Support:** Her ürün/varyant için çoklu görsel
- **Tag System:** PostgreSQL ArrayField ile etiketleme
- **Low Stock Alerts:** Minimum inventory level kontrolü

---

### 4. Operating (Operasyonlar)

**Amaç:** Siparişler, hammaddeler, üretim takibi.

#### Ana Modeller:

##### 4.1 RawMaterialGood
- **Açıklama:** Hammadde tanımları
- **Özellikler:**
  - `name`: Hammadde adı
  - `sku`: Stock Keeping Unit (auto-generate edilebilir)
  - `supplier_sku`: Tedarikçi SKU
  - `raw_type`: "direct" (doğrudan üretimde) veya "indirect" (genel gider)
  - `unit_of_measurement`: "units", "mt", "kg", "l", "bx"
  - `quantity`: Mevcut stok miktarı
- **Auto-SKU:** SKU girilmezse otomatik ID kullanılır

##### 4.2 RawMaterialGoodReceipt
- **Açıklama:** Hammadde alım fişleri
- **Özellikler:**
  - `book`: Hangi deftere ait (accounting.Book)
  - `currency`: Para birimi (accounting.CurrencyCategory)
  - `supplier`: Tedarikçi (crm.Supplier)
  - `receipt_number`: Fiş numarası
  - `invoice_number`: Fatura numarası
  - `date`: Alım tarihi
- **Constraint:** (supplier, receipt_number) unique
- **Property:** `amount` - Toplam tutar (items'lardan hesaplanır)
- **İlişki:** LiabilityAccountsPayable otomatik oluşturulur

##### 4.3 RawMaterialGoodItem
- **Açıklama:** Alım fişi kalemleri
- **Özellikler:**
  - `raw_material_good`: Hangi hammadde
  - `receipt`: Hangi fiş
  - `quantity`: Miktar
  - `unit_cost`: Birim maliyet
- **Otomatik İşlemler:**
  - RawMaterialGood.quantity'yi günceller
  - AssetInventoryRawMaterial oluşturur/günceller (commented out)

##### 4.4 WorkInProgressGood
- **Açıklama:** Yarı mamul ürünler (üretim aşamasında)
- **Özellikler:**
  - `product`: marketing.Product
  - `product_variant`: marketing.ProductVariant (opsiyonel)
  - `order`: Hangi sipariş için
  - `created_at`, `modified_at`: Zaman takibi

##### 4.5 Order (Sipariş)
- **Açıklama:** Müşteri siparişleri (model dosyada görünmüyor, views'da referans var)
- **Kullanım:**
  - EquityRevenue ile ilişkilendirilir
  - WorkInProgressGood ile bağlantılı

#### Önemli Özellikler:
- **FIFO/Average Costing:** Hammadde maliyet hesaplama
- **Automatic Inventory Updates:** Fiş kaydında otomatik stok güncelleme
- **Dual Material Types:** Direkt ve indirekt hammadde ayrımı
- **Receipt Tracking:** Unique receipt number kontrolü
- **Multi-Currency Support:** Farklı para birimlerinde alımlar

---

### 5. Authentication (Kimlik Doğrulama)

**Amaç:** Kullanıcı yönetimi ve yetkilendirme.

#### Ana Modeller:

##### 5.1 Permission
- **Açıklama:** Erişim seviyesi tanımları
- **Seçenekler:**
  - `admin`: Tam erişim
  - `manager`: Takım ve proje yönetimi
  - `employee`: Kendi görevleri
  - `guest`: Sınırlı görüntüleme
- **Özellikler:**
  - `name`: Permission adı
  - `description`: Açıklama

##### 5.2 Member
- **Açıklama:** Django User modelinin genişletilmiş versiyonu
- **Neden Ayrı Model:**
  - Django'nun base User modelini değiştirmek riskli
  - OneToOne ilişki ile senkronize
  - Ek özellikler eklemek için esneklik
- **Özellikler:**
  - `user`: OneToOne → Django User
  - `permissions`: ManyToMany → Permission
- **İlişkiler:**
  - StakeholderBook (muhasebe paydaşı)
  - EquityCapital (sermaye yatırımları)
  - EquityDivident (temettü ödemeleri)
  - Task (görev sorumlusu)

##### 5.3 Views (Görünümler)
- **signin:** Giriş yapma
- **signup:** Kullanıcı kaydı
- **signout:** Çıkış yapma
- **index:** Landing page

#### Önemli Özellikler:
- **Django User Extension:** User modeline dokunmadan genişletme
- **Permission System:** Esnek yetkilendirme
- **OneToOne Sync:** User ve Member senkronizasyonu

---

### 6. Todo (Görev Yönetimi)

**Amaç:** İş takibi ve görev yönetimi.

#### Ana Model:

##### 6.1 Task
- **Açıklama:** Görev kartları
- **Özellikler:**
  - `name`: Görev adı
  - `description`: Detaylı açıklama
  - `due_date`: Son tarih
  - `completed`: Tamamlandı mı?
  - `created_at`: Oluşturulma zamanı
  - `completed_at`: Tamamlanma zamanı
- **İlişkiler:**
  - `contact`: İrtibat kişisi için (opsiyonel)
  - `company`: Şirket için (opsiyonel)
  - `member`: Sorumlu kişi (opsiyonel)
- **Helper Methods:**
  - `get_delete_url()`: Silme URL'i

#### Önemli Özellikler:
- **Flexible Assignment:** Contact, Company veya Member'a atanabilir
- **Deadline Tracking:** Due date ile takip
- **Auto Member Assignment:** Save sırasında otomatik member atama

---

## Veritabanı Yapısı

### İlişki Diagramı (Önemli İlişkiler)

```
User (Django) 
  ↓ OneToOne
Member
  ↓ FK
StakeholderBook
  ↓ FK
Book ← Tüm finansal modeller

Company ← Contact (FK, optional)
  ↓ FK
CompanyFollowUp

Company/Contact ← Note (FK)
Company/Contact ← Task (FK, optional)
Company/Contact/Supplier ← AccountsReceivable (FK)

Supplier
  ↓ FK
RawMaterialGoodReceipt → RawMaterialGoodItem → RawMaterialGood
  ↓ FK
LiabilityAccountsPayable

Product
  ├── ProductVariant (FK)
  │     ↓ M2M
  │   ProductVariantAttributeValue ← ProductVariantAttribute (FK)
  ├── ProductFile (FK)
  └── Category, Collection (FK/M2M)

Product/ProductVariant ← Order ← WorkInProgressGood
Order ← EquityRevenue (FK)

CashAccount ← Tüm Equity modelleri (FK)
  ↓ FK
CurrencyCategory

CashTransactionEntry (Generic FK) → Tüm finansal işlemler
```

### Önemli Constraint'ler
- **Book:** `name` unique
- **CashAccount:** (book, name, currency) unique constraint
- **Company:** `name` unique
- **CurrencyCategory:** `code` unique, `name` unique
- **Product:** `sku` unique
- **ProductVariantAttributeValue:** (attribute, value) unique
- **RawMaterialGoodReceipt:** (supplier, receipt_number) unique

---

## Önemli Özellikler

### 1. Multi-Currency Support
- Her işlem kendi para biriminde kaydedilir
- Otomatik döviz kuru güncellemesi
- Raporlarda base currency'ye dönüşüm

### 2. Cloudinary Integration
- Tüm ürün görselleri CDN'de
- Otomatik optimizasyon (format, quality)
- Django signals ile entegrasyon

### 3. Generic Relations
- CashTransactionEntry herhangi bir modele bağlanabilir
- ContentType kullanımı
- Esnek audit trail

### 4. Follow-up Email Automation
- Otomatik prospect takibi
- 5 aşamalı email dizisi
- Management command ile cron job entegrasyonu

### 5. Running Balance Calculation
- Her işlemde kümülatif bakiye
- Multi-currency aggregate
- Performance optimized

### 6. Variant System
- Esnek özellik sistemi
- Attribute-Value pattern
- Auto-format (lowercase, underscore)

### 7. HTMX Integration
- Dynamic form interactions
- Partial page updates
- Better UX without heavy JS framework

---

## Kurulum ve Çalıştırma

### 1. Gereksinimler
```bash
Python 3.8+
PostgreSQL 12+
```

### 2. Proje Kurulumu
```bash
# Repository'yi klonlayın
git clone https://github.com/nejum-org/erp.git
cd erp

# Virtual environment oluşturun
python -m venv vir_env
.\vir_env\Scripts\activate  # Windows
source vir_env/bin/activate  # Linux/Mac

# Bağımlılıkları yükleyin
pip install -r requirements.txt
```

### 3. Environment Variables (.env)
```env
SECRET_KEY=your-secret-key
DEBUG=True

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=erp_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Cloudinary
cloudinary_cloud_name=your-cloud-name
cloudinary_api_key=your-api-key
cloudinary_api_secret=your-api-secret

# Email (Gmail SMTP)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
FOLLOWUP_EMAIL_FROM=sales@yourcompany.com
FOLLOWUP_SENDER_NAME=Your Company
FOLLOWUP_SENDER_TITLE=Sales Team
FOLLOWUP_SENDER_COMPANY=Your Company Name
```

### 4. Database Migration
```bash
python manage.py migrate
```

### 5. Superuser Oluşturma
```bash
python manage.py createsuperuser
```

### 6. Static Files Toplama
```bash
python manage.py collectstatic
```

### 7. Development Server
```bash
python manage.py runserver
```

### 8. Follow-up Email Cron Job (Production)
```bash
# Günlük çalıştır (örn: her sabah 9:00)
0 9 * * * cd /path/to/erp && python manage.py send_followup_emails
```

---

## Deployment

### Vercel
- `vercel.json` yapılandırması mevcut
- WSGI app: `erp.wsgi.app`

### Render
- PostgreSQL database
- Gunicorn web server
- WhiteNoise static files

### Environment
- **Production:** DEBUG=False
- **Static Files:** WhiteNoise ile compressed serving
- **Media Files:** Cloudinary CDN

---

## Lisans

**GNU Affero General Public License v3.0**

Bu proje AGPL-3.0 lisansı altında açık kaynak olarak geliştirilmektedir.

---

## Katkıda Bulunma

Proje henüz topluluk katkılarına açılıyor. Yakında:
- Public roadmap
- Contribution guide
- Discord/forum

---

## İletişim

**Organization:** nejum-org  
**GitHub:** https://github.com/nejum-org/erp  
**Website:** nejum.com

---

**Son Güncelleme:** 2025-10-21  
**Proje Versiyonu:** Beta  
**Django Version:** 4.2.4
