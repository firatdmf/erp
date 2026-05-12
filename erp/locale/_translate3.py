"""Final pass: translate the remaining specific strings."""
import polib, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

EXTRA = {
    "BLOG": "BLOG", "Blog": "Blog",
    "Assign To": "Ata", "Assign to": "Ata",
    "Attach Contact": "Kişi Ekle", "Attachments (Google Drive)": "Ekler (Google Drive)",
    "BALANCE": "BAKİYE", "BARCODE": "BARKOD",
    "Background info": "Arkaplan bilgisi", "Basic Informationnn": "Temel Bilgiler",
    "Bcc": "Gizli Kopya",
    "Books": "Defterler", "Box": "Kutu",
    "CATEGORY": "KATEGORİ", "CRM Index": "CRM Anasayfa", "CURRENCY": "PARA BİRİMİ",
    "Carrier": "Taşıyıcı", "Category (EN)": "Kategori (EN)", "Category (PL)": "Kategori (PL)",
    "Category (RU)": "Kategori (RU)", "Category (Turkish) *": "Kategori (Türkçe) *",
    "Cc": "Kopya", "Channel Logs": "Kanal Günlükleri",
    "Click to add": "Eklemek için tıkla", "Click to copy": "Kopyalamak için tıkla",
    "Combined": "Birleşik", "Confirm Login": "Girişi Onayla",
    "Contact Details": "Kişi Ayrıntıları", "Contact Information": "Kişi Bilgileri",
    "Contact Person": "İlgili Kişi", "Conversion": "Dönüşüm",
    "Currency Exchange": "Döviz Çevirisi", "Custom": "Özel",
    "Customer Information": "Müşteri Bilgileri",

    "DATE": "TARİH", "DESCRIPTION": "AÇIKLAMA", "DISCOUNT": "İNDİRİM",
    "DUE DATE": "VADE TARİHİ",
    "Daily Activity": "Günlük Etkinlik", "Daily Sales": "Günlük Satışlar",
    "Date Range": "Tarih Aralığı", "Default Currency": "Varsayılan Para Birimi",
    "Delete Item": "Kalemi Sil", "Description (EN)": "Açıklama (EN)",
    "Description (PL)": "Açıklama (PL)", "Description (RU)": "Açıklama (RU)",
    "Description (Turkish) *": "Açıklama (Türkçe) *",
    "Discount Code": "İndirim Kodu", "Discount Percentage": "İndirim Yüzdesi",
    "Document": "Belge", "Documents": "Belgeler",

    "EMAIL": "E-POSTA", "Edit Order": "Siparişi Düzenle",
    "Equity": "Özkaynak", "Equity Account": "Özkaynak Hesabı",
    "Expense Category": "Gider Kategorisi",

    "FILE": "DOSYA", "Field Name": "Alan Adı",
    "Files": "Dosyalar", "Final Amount": "Nihai Tutar", "Finance": "Finans",
    "Finished Goods": "Mamul Mallar", "Fixed Asset": "Sabit Varlık",
    "Forgot": "Unuttum", "From Date": "Başlangıç Tarihi",

    "Generate": "Oluştur", "Gmail Connection": "Gmail Bağlantısı",
    "Hide": "Gizle", "Highest": "En Yüksek",

    "INVOICE": "FATURA", "ITEM": "KALEM",
    "Inactive Members": "Pasif Üyeler",
    "Influencer": "Fenomen", "Internal": "Dahili",
    "Item Name": "Kalem Adı", "Item Type": "Kalem Türü",

    "Just now": "Az önce",
    "Keep editing": "Düzenlemeye devam et",
    "Last Activity": "Son Etkinlik", "Last Login": "Son Giriş",
    "Last Modified": "Son Değişiklik", "Lead": "Aday",
    "Liability": "Yükümlülük", "Liquid Asset": "Likit Varlık",
    "Live Stock": "Canlı Stok", "Lock": "Kilitle", "Locked": "Kilitli",

    "MESSAGES": "MESAJLAR", "MORE": "DAHA",
    "Mailbox": "Posta Kutusu", "Make Default": "Varsayılan Yap",
    "Mark Complete": "Tamamlandı İşaretle", "Member List": "Üye Listesi",
    "Member Name": "Üye Adı", "Members Online": "Çevrimiçi Üyeler",
    "Min Inventory": "Min Stok", "Modal": "Modal",
    "Money In": "Gelen Para", "Money Out": "Giden Para", "Monthly Sales": "Aylık Satışlar",

    "NAME": "AD", "NOTES": "NOTLAR",
    "New Account": "Yeni Hesap", "New Activity": "Yeni Etkinlik",
    "New Note": "Yeni Not", "New Order": "Yeni Sipariş",
    "Newsletter": "Bülten",
    "No description provided.": "Açıklama yok.",
    "Not Set": "Ayarlı değil",

    "ORDER": "SİPARİŞ", "Online Members": "Çevrimiçi Üyeler",
    "Open Tasks": "Açık Görevler", "Overview": "Genel Bakış",

    "PAID": "ÖDENDİ", "Page Not Found": "Sayfa Bulunamadı",
    "Past Activity": "Geçmiş Etkinlik", "Pending Approval": "Onay Bekliyor",
    "Pending Tasks": "Bekleyen Görevler", "Permission Denied": "İzin Reddedildi",
    "Personal Tasks": "Kişisel Görevler", "Phone Numbers": "Telefon Numaraları",
    "Place Order": "Sipariş Ver", "Plain Text": "Düz Metin",
    "Posted by": "Gönderen", "Post a Message": "Mesaj Gönder",
    "Procurement Officer": "Satın Alma Yetkilisi", "Product Categories": "Ürün Kategorileri",
    "Product Code": "Ürün Kodu", "Product Variants": "Ürün Varyantları",
    "Promotion": "Promosyon", "Pull from Gmail": "Gmail'den Çek",
    "Purchase Date": "Satın Alma Tarihi",

    "QUANTITY": "MİKTAR",
    "Quick Actions": "Hızlı İşlemler", "Quick Note": "Hızlı Not",

    "RECEIPT": "FİŞ", "Read Time": "Okunma Süresi",
    "Receipt Items": "Fiş Kalemleri", "Receivable": "Alacak",
    "Recipient": "Alıcı", "Recipients": "Alıcılar",
    "Record": "Kayıt", "Records": "Kayıtlar",
    "Refresh Inbox": "Gelen Kutusunu Yenile", "Region Settings": "Bölge Ayarları",
    "Reorder": "Yeniden Sırala",
    "Report a Bug": "Hata Bildir", "Report Issue": "Sorun Bildir",
    "Resource": "Kaynak", "Revenue Total": "Toplam Gelir",
    "Role Name": "Rol Adı", "Run": "Çalıştır",

    "SALES": "SATIŞLAR", "STATUS": "DURUM",
    "Sales Channel": "Satış Kanalı", "Sales Person": "Satış Temsilcisi",
    "Save & New": "Kaydet ve Yeni",
    "Search Channel": "Kanal Ara", "Search Contacts": "Kişilerde Ara",
    "Search Customers": "Müşterilerde Ara", "Search Members": "Üyelerde Ara",
    "Search Notes": "Notlarda Ara", "Search Orders": "Siparişlerde Ara",
    "Search Products": "Ürünlerde Ara", "Search Suppliers": "Tedarikçilerde Ara",
    "Search Tasks": "Görevlerde Ara", "Search Users": "Kullanıcılarda Ara",
    "Section Name": "Bölüm Adı", "Send invitation": "Davet Gönder",
    "Set Default": "Varsayılan Yap", "Set due date": "Vade tarihi belirle",
    "Set Priority": "Öncelik belirle", "Setup": "Kurulum",
    "Show Less": "Daha Az Göster", "Show Password": "Parolayı Göster",
    "Side Panel": "Yan Panel", "Single Record": "Tek Kayıt",
    "Site Settings": "Site Ayarları", "Snooze": "Ertele",
    "Source Currency": "Kaynak Para Birimi", "Status Update": "Durum Güncelle",
    "Stock Level": "Stok Seviyesi", "Sub Category": "Alt Kategori",
    "Sub-Total": "Ara Toplam", "Subscribe": "Abone Ol",

    "TITLE": "BAŞLIK", "TOTAL": "TOPLAM",
    "Take Note": "Not Al", "Target Currency": "Hedef Para Birimi",
    "Tax Amount": "Vergi Tutarı", "Team Settings": "Takım Ayarları",
    "Template": "Şablon", "Threshold": "Eşik", "Time Spent": "Harcanan Süre",
    "Title (EN)": "Başlık (EN)", "Title (PL)": "Başlık (PL)",
    "Title (RU)": "Başlık (RU)", "Title (Turkish) *": "Başlık (Türkçe) *",
    "To Date": "Bitiş Tarihi", "Top Customers": "En İyi Müşteriler",
    "Top Products": "En İyi Ürünler", "Top Sellers": "En Çok Satanlar",
    "Total Orders": "Toplam Siparişler",
    "Total Products": "Toplam Ürünler", "Total Revenue": "Toplam Gelir",
    "Total Stock": "Toplam Stok", "Track Order": "Siparişi Takip Et",
    "Transaction": "İşlem", "Transactions": "İşlemler",
    "Translation": "Çeviri", "Trial": "Deneme",

    "UNIT": "BİRİM", "Unarchive": "Arşivden Çıkar",
    "Unsent": "Gönderilmemiş",
    "Unsubscribe": "Aboneliği iptal et", "Untitled": "Başlıksız",
    "Update Avatar": "Avatarı Güncelle",
    "Use Default": "Varsayılanı Kullan",
    "User Name": "Kullanıcı Adı", "User Settings": "Kullanıcı Ayarları",

    "VAT": "KDV", "Validate": "Doğrula", "Variant Name": "Varyant Adı",
    "View Order": "Siparişi Görüntüle",
    "View Receipt": "Fişi Görüntüle", "View Task": "Görevi Görüntüle",

    "Welcome back!": "Tekrar hoş geldin!", "Whole Team": "Tüm Takım",
    "Wholesale": "Toptan", "Wholesale Price": "Toptan Fiyat",

    "Yearly Sales": "Yıllık Satışlar", "Your Cart": "Sepetin",
    "Your Order": "Siparişin", "Your Orders": "Siparişlerin",
    "Your Profile": "Profilin",
}

po = polib.pofile(r"C:/Users/enes3/erp/erp/locale/tr/LC_MESSAGES/django.po")
existing_map = {e.msgid: e for e in po}
updated = 0
for src, dst in EXTRA.items():
    if src in existing_map:
        if existing_map[src].msgstr == src or not existing_map[src].msgstr:
            existing_map[src].msgstr = dst
            updated += 1
    else:
        po.append(polib.POEntry(msgid=src, msgstr=dst))
        updated += 1
po.save(r"C:/Users/enes3/erp/erp/locale/tr/LC_MESSAGES/django.po")
po.save_as_mofile(r"C:/Users/enes3/erp/erp/locale/tr/LC_MESSAGES/django.mo")

translated = sum(1 for e in po if e.msgstr and e.msgstr != e.msgid)
fallback   = sum(1 for e in po if e.msgstr == e.msgid)
print(f"Updated/added: {updated}")
print(f"Fully translated: {translated}")
print(f"Still EN fallback: {fallback}")
print(f"Total: {len(po)}")
