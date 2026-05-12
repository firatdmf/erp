"""Bulk-translate extracted strings into the TR .po/.mo file."""
import polib, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

extracted_path = Path(__file__).with_name("_extracted_strings.txt")
extracted = [s.strip() for s in extracted_path.read_text(encoding="utf-8").splitlines() if s.strip()]
print(f"Loaded {len(extracted)} extracted strings")

TR = {
    # --- Common UI verbs ---
    "Save": "Kaydet", "Save Changes": "Değişiklikleri Kaydet", "Cancel": "İptal", "Close": "Kapat",
    "Delete": "Sil", "Edit": "Düzenle", "View": "Görüntüle", "Add": "Ekle", "Create": "Oluştur",
    "Update": "Güncelle", "Confirm": "Onayla", "Submit": "Gönder", "Search": "Ara",
    "Filter": "Filtrele", "Sort": "Sırala", "Reset": "Sıfırla", "Apply": "Uygula",
    "Back": "Geri", "Next": "İleri", "Previous": "Önceki", "Continue": "Devam et",
    "Done": "Tamam", "Loading…": "Yükleniyor…", "Loading...": "Yükleniyor...",
    "Yes": "Evet", "No": "Hayır", "OK": "Tamam", "Discard": "Vazgeç",
    "Send": "Gönder", "Reply": "Yanıtla", "Forward": "Yönlendir", "Refresh": "Yenile",
    "Export": "Dışa Aktar", "Import": "İçe Aktar", "Download": "İndir", "Upload": "Yükle",
    "Print": "Yazdır", "Copy": "Kopyala", "Paste": "Yapıştır", "Duplicate": "Çoğalt",
    "Archive": "Arşivle", "Restore": "Geri Yükle", "Remove": "Kaldır", "Clear": "Temizle",

    # --- Status / state ---
    "Active": "Aktif", "Inactive": "Pasif", "Pending": "Beklemede", "Approved": "Onaylandı",
    "Rejected": "Reddedildi", "Draft": "Taslak", "Published": "Yayımlandı", "Archived": "Arşivlendi",
    "Completed": "Tamamlandı", "In Progress": "Devam ediyor", "Cancelled": "İptal Edildi",
    "Open": "Açık", "Closed": "Kapalı", "Paid": "Ödendi", "Unpaid": "Ödenmedi",
    "Featured": "Öne çıkan", "New": "Yeni", "Hot": "Popüler", "Sold": "Satıldı",
    "Out of stock": "Stok yok", "Low stock": "Az stok", "In stock": "Stokta",

    # --- Generic UI labels ---
    "Title": "Başlık", "Name": "Ad", "First Name": "Ad", "Last Name": "Soyad",
    "Full name": "Tam ad", "Username": "Kullanıcı adı", "Password": "Parola",
    "Email": "E-posta", "Email Address": "E-posta Adresi", "Phone": "Telefon",
    "Address": "Adres", "City": "Şehir", "Country": "Ülke", "Zip code": "Posta kodu",
    "Date": "Tarih", "Time": "Saat", "Date & Time": "Tarih ve Saat", "Created": "Oluşturuldu",
    "Created at": "Oluşturulma tarihi", "Updated": "Güncellendi", "Updated at": "Güncellenme tarihi",
    "Description": "Açıklama", "Notes": "Notlar", "Note": "Not", "Tags": "Etiketler",
    "Status": "Durum", "Type": "Tür", "Category": "Kategori", "Categories": "Kategoriler",
    "Subcategory": "Alt kategori", "Owner": "Sahip", "Author": "Yazar", "Assignee": "Atanan kişi",
    "Priority": "Öncelik", "Action": "İşlem", "Actions": "İşlemler", "Details": "Ayrıntılar",
    "Information": "Bilgi", "Settings": "Ayarlar", "Preferences": "Tercihler",
    "Options": "Seçenekler", "Option": "Seçenek", "Other": "Diğer",
    "All": "Tümü", "Total": "Toplam", "Subtotal": "Ara toplam", "Tax": "Vergi",
    "Discount": "İndirim", "Quantity": "Adet", "Amount": "Tutar", "Price": "Fiyat",
    "Cost": "Maliyet", "Currency": "Para birimi", "Stock": "Stok", "SKU": "SKU",
    "Barcode": "Barkod", "Weight": "Ağırlık", "Dimensions": "Boyutlar", "Vendor": "Tedarikçi",
    "Customer": "Müşteri", "Customers": "Müşteriler", "Supplier": "Tedarikçi", "Suppliers": "Tedarikçiler",
    "Member": "Üye", "Members": "Üyeler", "Role": "Rol", "Roles": "Roller",
    "Permission": "İzin", "Permissions": "İzinler", "Group": "Grup", "Groups": "Gruplar",

    # --- Navigation / pages ---
    "Dashboard": "Pano", "Home": "Ana Sayfa", "Profile": "Profil", "Account": "Hesap",
    "Logout": "Çıkış Yap", "Sign Out": "Çıkış Yap", "Login": "Giriş Yap", "Sign In": "Giriş Yap",
    "Sign Up": "Kayıt Ol", "Register": "Kaydol",
    "My Team": "Takımım", "My Tasks": "Görevlerim", "My Orders": "Siparişlerim",
    "Team Members": "Takım Üyeleri", "Team Overview": "Takım Genel Bakış",
    "Tasks": "Görevler", "Task": "Görev", "Messages": "Mesajlar", "Message": "Mesaj",
    "Meetings": "Toplantılar", "Meeting": "Toplantı", "Schedule Meeting": "Toplantı Planla",
    "Manage Members": "Üyeleri Yönet", "Manage Roles": "Rolleri Yönet",
    "Notifications": "Bildirimler", "Favorites": "Favoriler", "Inbox": "Gelen Kutusu",

    # --- Module names ---
    "Accounting": "Muhasebe", "Marketing": "Pazarlama", "Operations": "Operasyon",
    "Procurement": "Satın Alma", "Mail": "Posta", "Analytics": "Analitik",
    "Reports": "Raporlar", "Inventory": "Envanter", "Shipping": "Kargo",
    "Pricing": "Fiyatlandırma", "Packaging": "Paketleme",
    "Sales": "Satışlar", "Purchases": "Satın Almalar",
    "Products": "Ürünler", "Product": "Ürün", "Orders": "Siparişler", "Order": "Sipariş",
    "Contacts": "Kişiler", "Contact": "Kişi", "Companies": "Şirketler", "Company": "Şirket",
    "Warehouses": "Depolar", "Warehouse": "Depo",
    "Raw Materials": "Hammaddeler", "Raw Material": "Hammadde",
    "Blog": "Blog", "Blog post": "Blog yazısı", "Email Campaigns": "E-posta Kampanyaları",
    "Email Automation": "E-posta Otomasyonu", "My Emails": "E-postalarım",

    # --- Product form ---
    "General Information": "Genel Bilgiler", "Media": "Medya", "Variants": "Varyantlar",
    "Manufacturing Recipe (BOM)": "Üretim Reçetesi (BOM)", "Sales Channels": "Satış Kanalları",
    "Campaign / Discount": "Kampanya / İndirim", "Product Information": "Ürün Bilgileri",
    "Product Attributes": "Ürün Özellikleri", "Product Organization": "Ürün Organizasyonu",
    "Product Type": "Ürün Türü", "Product Name": "Ürün Adı", "Cost per item": "Birim maliyet",
    "Online Store": "Online Mağaza", "Listed on website": "Web sitesinde listeleniyor",
    "Point of Sale": "Satış Noktası", "Selling policy enabled": "Satış politikası aktif",
    "Sold as a pack": "Paket halinde satılıyor", "Items per pack": "Paket başına adet",
    "Min. Inventory Level": "Min. Stok Seviyesi", "Care Instructions": "Bakım Talimatları",
    "Additional Info": "Ek Bilgi", "Edit Variant": "Varyantı Düzenle",
    "Edit Product": "Ürünü Düzenle", "Save Product": "Ürünü Kaydet",
    "Add product": "Ürün ekle", "Add Product": "Ürün Ekle", "Create product": "Ürün oluştur",
    "Product list": "Ürün listesi", "Product List": "Ürün Listesi",
    "Back to Products": "Ürünlere Dön", "Uncategorized": "Kategorisiz",
    "Add option": "Seçenek ekle", "Add variant": "Varyant ekle",
    "Add tier": "Kademe ekle", "Add new category": "Yeni kategori ekle",

    # --- Campaign panel ---
    "None": "Yok", "No discount": "İndirim yok",
    "Flat % off": "Sabit % indirim", "Until a date": "Belirli bir tarihe kadar",
    "Volume tiers": "Kademeli adet", "By quantity": "Adete göre",
    "Discount (%)": "İndirim (%)", "Ends on": "Bitiş tarihi",

    # --- Languages ---
    "English": "İngilizce", "Turkish": "Türkçe", "Russian": "Rusça", "Polish": "Lehçe",
    "Language": "Dil",

    # --- Settings ---
    "Workspace": "Çalışma Alanı", "Workspace Tools": "Çalışma Alanı Araçları",
    "Theme Preference": "Tema Tercihi", "Light Mode": "Açık Mod", "Dark Mode": "Koyu Mod",
    "App Settings": "Uygulama Ayarları", "App Preferences": "Uygulama Tercihleri",
    "Profile Settings": "Profil Ayarları", "Security": "Güvenlik",
    "Integrations": "Entegrasyonlar", "Sales & CRM": "Satış & CRM",
    "Connected": "Bağlı", "Disconnect": "Bağlantıyı Kes", "Connect Google": "Google'ı Bağla",
    "Send & Receive": "Gönder & Al", "Not connected": "Bağlı değil",
    "Requires Google": "Google gerektirir", "Soon": "Yakında",
    "General": "Genel",
    "Update Password": "Parolayı Güncelle", "Current Password": "Mevcut Parola",
    "New Password": "Yeni Parola", "Confirm New Password": "Yeni Parolayı Onayla",
    "Password Requirements": "Parola Gereksinimleri",
    "Minimum 8 characters long": "En az 8 karakter uzunluğunda",
    "At least one uppercase letter": "En az bir büyük harf",
    "At least one number": "En az bir rakam",
    "At least one special character": "En az bir özel karakter",

    # --- Top bar ---
    "Search...": "Ara...", "Search…": "Ara…", "RECENT SEARCHES": "SON ARAMALAR",
    "Clear history": "Geçmişi temizle", "Search for something...": "Birşey aramaya başla...",
    "No new notifications": "Yeni bildirim yok", "Clear selection": "Seçimi temizle",
    "Set as primary image": "Ana görsel olarak ayarla",
    "Describe this image for SEO": "SEO için bu görseli tanımla",
    "Enter product name...": "Ürün adı girin...",
    "Search by product name, SKU or barcode…": "Ürün adı, SKU veya barkod ile ara…",
    "Search collections...": "Koleksiyonlarda ara...",
    "Search raw materials to add...": "Eklemek için hammaddelerde ara...",

    # --- Team ---
    "Create Team": "Takım Oluştur", "Create New Team": "Yeni Takım Oluştur",
    "Team Name *": "Takım Adı *", "Team Name": "Takım Adı",
    "Icon Color": "Simge Rengi", "All Teams": "Tüm Takımlar",
    "No teams yet": "Henüz takım yok",
    "Add Member": "Üye Ekle", "Add Member to Team": "Takıma Üye Ekle",
    "Search User": "Kullanıcı Ara",
    "Date Added": "Eklenme Tarihi", "Remove Member": "Üyeyi Çıkar",
    "Add to Favorites": "Favorilere Ekle", "Archive Team": "Takımı Arşivle",

    # --- Tasks / Kanban ---
    "Create Task": "Görev Oluştur", "Add New Section": "Yeni Bölüm Ekle",
    "Add Section": "Bölüm Ekle", "Section Title": "Bölüm Başlığı",
    "Color Tag": "Renk Etiketi", "Edit Section": "Bölümü Düzenle",
    "Save Section": "Bölümü Kaydet", "Move Left": "Sola Taşı", "Move Right": "Sağa Taşı",
    "Board": "Pano", "List": "Liste",
    "Edit Task": "Görevi Düzenle", "Delete Task": "Görevi Sil",
    "View Details": "Ayrıntıları Görüntüle",
    "Schedule Meeting": "Toplantı Planla",
    "Upcoming Meetings": "Yaklaşan Toplantılar", "Meeting History": "Toplantı Geçmişi",
    "Title *": "Başlık *", "Date & Time *": "Tarih ve Saat *",
    "Duration (min)": "Süre (dk)", "Participants": "Katılımcılar",
    "Location / Link": "Konum / Bağlantı", "Meeting Type": "Toplantı Türü",
    "Team": "Takım", "Individual": "Bireysel", "Select Team": "Takım Seç",
    "Generate Google Meet Link": "Google Meet Bağlantısı Oluştur",

    # --- Messages ---
    "Direct Messages": "Doğrudan Mesajlar",
    "Channels": "Kanallar", "Create Channel": "Kanal Oluştur",
    "Channel Name *": "Kanal Adı *",
    "Quick Find": "Hızlı Bul", "Google Chat": "Google Sohbet",
    "TODAY": "BUGÜN", "Today": "Bugün",
    "System Operational": "Sistem Çalışıyor",
    "No channels yet": "Henüz kanal yok",
    "No other team members": "Başka takım üyesi yok",
    "Select a conversation": "Bir sohbet seç",

    # --- Empty / generic states ---
    "No data": "Veri yok", "No items": "Öğe yok", "No results": "Sonuç yok",
    "No matching products found": "Eşleşen ürün bulunamadı", "Showing": "Gösteriliyor",

    # --- Counts ---
    "products": "ürün", "variants": "varyant", "low stock": "az stok",
    "out of stock": "stok yok", "products shown": "ürün gösteriliyor",
    "Select all": "Tümünü seç", "CATALOG": "KATALOG",

    # --- Headers ---
    "VARIANT": "VARYANT", "ATTRIBUTES": "ÖZELLİKLER", "STOCK": "STOK", "PRICE": "FİYAT",
    "PRODUCTS": "ÜRÜNLER", "ORDERS": "SİPARİŞLER", "CUSTOMERS": "MÜŞTERİLER",
    "SUPPLIERS": "TEDARİKÇİLER", "WAREHOUSE": "DEPO", "RAW MATERIAL": "HAMMADDE",
    "PURCHASING": "SATIN ALMA", "TEAM MANAGEMENT": "TAKIM YÖNETİMİ",
    "ADD SINGLE RECORD": "TEKİL KAYIT EKLE", "LEDGERS": "DEFTERLER", "REPORTS": "RAPORLAR",
    "QR ACTIONS": "KARE-KOD İŞLEMLERİ", "BLOG": "BLOG",

    # --- File / image ---
    "Alt text": "Alternatif metin", "File name": "Dosya adı", "Upload New": "Yeni Yükle",
    "Used in": "Kullanıldığı yerler", "Total Cost": "Toplam Maliyet", "Unit Cost": "Birim Maliyet",
    "Qty Used": "Kullanılan Miktar", "Unit": "Birim", "New Category": "Yeni Kategori",
    "SKU (Stock Keeping Unit)": "SKU (Stok Kodu)",
    "Barcode (ISBN, UPC, GTIN, etc.)": "Barkod (ISBN, UPC, GTIN, vb.)",
    "Recently updated": "Son güncellenen", "By name": "İsme göre",
    "Collections": "Koleksiyonlar", "e.g. pack of 12, pack of 5": "örn. 12'li paket, 5'li paket",

    # --- Common chat / message ---
    "Bold": "Kalın", "Italic": "İtalik",
    "Strikethrough": "Üstü çizili",
    "Attach file": "Dosya ekle", "Add emoji": "Emoji ekle", "Mention": "Bahset",
    "Mention a teammate": "Bir takım arkadaşından bahset",
    "Emoji": "Emoji", "No teammates available": "Takım arkadaşı yok",

    # --- Module words ---
    "Add new record": "Yeni kayıt ekle",
    "View ledgers": "Defterleri görüntüle", "Create ledger": "Defter oluştur",
    "Sales dashboard": "Satış panosu", "Sales Dashboard": "Satış Panosu",
    "Team members": "Takım üyeleri", "Assign task": "Görev ata",
    "Manage roles": "Rolleri yönet", "Schedule meeting": "Toplantı planla",
    "QR scan": "QR tarama", "QR scan package": "Paket QR tarama",
    "Raw material list": "Hammadde listesi", "Create raw material": "Hammadde oluştur",
    "Raw material receipt": "Hammadde girişi", "Raw material item": "Hammadde kalemi",
    "Create order": "Sipariş oluştur", "Order list": "Sipariş listesi",
    "My warehouses": "Depolarım", "Add warehouse": "Depo ekle",
    "Purchase requests": "Satın alma talepleri", "Purchase orders": "Satın alma siparişleri",
    "Supplier list": "Tedarikçi listesi", "Add supplier": "Tedarikçi ekle",
    "Email automation": "E-posta otomasyonu",
    "Create blog post": "Blog yazısı oluştur", "Blog list": "Blog listesi",

    # --- Misc UI ---
    "Welcome, %(first)s %(last)s!": "Hoş geldin, %(first)s %(last)s!",
    "More integrations": "Daha fazla entegrasyon",
    "Notification Settings Coming Soon": "Bildirim Ayarları Yakında",
}

po = polib.pofile(r"C:/Users/enes3/erp/erp/locale/tr/LC_MESSAGES/django.po")
existing = {e.msgid for e in po}

added = 0
needs_translation = []
for s in extracted:
    if s in existing:
        continue
    if s in TR:
        po.append(polib.POEntry(msgid=s, msgstr=TR[s]))
        added += 1
    else:
        po.append(polib.POEntry(msgid=s, msgstr=s))
        needs_translation.append(s)
        added += 1

# Also ensure all explicit TR entries are present
for src, dst in TR.items():
    if src not in existing and not any(e.msgid == src for e in po):
        po.append(polib.POEntry(msgid=src, msgstr=dst))
        added += 1

po.save(r"C:/Users/enes3/erp/erp/locale/tr/LC_MESSAGES/django.po")
po.save_as_mofile(r"C:/Users/enes3/erp/erp/locale/tr/LC_MESSAGES/django.mo")
print(f"Total entries: {len(po)} (+{added} added)")
print(f"Strings still using EN fallback (need manual TR): {len(needs_translation)}")
print("First 30 to translate later:")
for s in needs_translation[:30]:
    print("  -", s)
