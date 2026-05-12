"""Second-pass translator: covers ALL remaining EN-fallback strings."""
import polib, sys, io, re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Big extension covering common ERP/admin patterns
EXTRA_TR = {
    # Common 'Add X' patterns
    "Add Another File": "Başka Dosya Ekle",
    "Add Contact": "Kişi Ekle",
    "Add Equity Capital": "Sermaye Ekle",
    "Add Equity Expense": "Gider Ekle",
    "Add Equity Revenue": "Gelir Ekle",
    "Add File": "Dosya Ekle",
    "Add File (Optional)": "Dosya Ekle (İsteğe Bağlı)",
    "Add Item to Receipt": "Fişe Kalem Ekle",
    "Add New Product": "Yeni Ürün Ekle",
    "Add Note": "Not Ekle",
    "Add Raw Material": "Hammadde Ekle",
    "Add Receipt": "Fiş Ekle",
    "Add Supplier": "Tedarikçi Ekle",
    "Add Task": "Görev Ekle",
    "Add a Company": "Şirket Ekle",
    "Add a Contact": "Kişi Ekle",
    "Add a single record": "Tek bir kayıt ekle",
    "Add another item": "Başka kalem ekle",
    "Add new records": "Yeni kayıtlar ekle",
    "Add Customer": "Müşteri Ekle",
    "Add Order": "Sipariş Ekle",
    "Add Section": "Bölüm Ekle",
    "Add Variant": "Varyant Ekle",
    "Add Field": "Alan Ekle",
    "Add Member": "Üye Ekle",
    "Add Channel": "Kanal Ekle",

    # 'All X' patterns
    "All Materials": "Tüm Malzemeler",
    "All Notes": "Tüm Notlar",
    "All Time": "Tüm Zamanlar",
    "All Orders": "Tüm Siparişler",
    "All Tasks": "Tüm Görevler",
    "All Products": "Tüm Ürünler",
    "All Contacts": "Tüm Kişiler",
    "All Companies": "Tüm Şirketler",
    "All Suppliers": "Tüm Tedarikçiler",
    "All Customers": "Tüm Müşteriler",
    "All Categories": "Tüm Kategoriler",

    # Misc common
    "Account Balance": "Hesap Bakiyesi",
    "Activity report": "Etkinlik raporu",
    "Activity Log": "Etkinlik Günlüğü",
    "Activity": "Etkinlik",
    "Additional Details": "Ek Ayrıntılar",
    "Addresses": "Adresler",
    "Admin": "Yönetici",
    "American": "Amerikan",
    "Amount Paid": "Ödenen Tutar",
    "Amount Due": "Ödenecek Tutar",
    "Approve": "Onayla",
    "Approved": "Onaylandı",
    "Approver": "Onaylayan",
    "Archived Messages": "Arşivlenmiş Mesajlar",
    "Are you sure?": "Emin misin?",
    "Assigned Tasks": "Atanan Görevler",
    "Assigned to me": "Bana atananlar",
    "Assigned to": "Atanan",
    "Assignees": "Atananlar",
    "Attach": "Ekle",
    "Attachment": "Ek",
    "Attachments": "Ekler",
    "Attribute": "Özellik",
    "Avatar": "Avatar",

    "Background Info": "Arkaplan Bilgisi",
    "Balance": "Bakiye",
    "Beta": "Beta",
    "Billing": "Faturalandırma",
    "Birthday": "Doğum Günü",
    "Booked": "Rezerve",

    "Calendar": "Takvim", "Calendar View": "Takvim Görünümü",
    "Call": "Ara", "Capacity": "Kapasite", "Card": "Kart",
    "Change Password": "Parola Değiştir", "Channel": "Kanal",
    "Chat": "Sohbet", "Check": "Kontrol Et", "Checked": "İşaretli",
    "Choose File": "Dosya Seç", "Chosen": "Seçildi", "Clear": "Temizle",
    "Click here": "Buraya tıkla", "Click to upload": "Yüklemek için tıkla",
    "Closed": "Kapalı", "Code": "Kod", "Color": "Renk",
    "Comment": "Yorum", "Comments": "Yorumlar", "Communications": "İletişim",
    "Complete": "Tamamla", "Complete Task": "Görevi Tamamla",
    "Confirm Delete": "Silmeyi Onayla", "Confirm Password": "Parolayı Onayla",
    "Conversation": "Sohbet", "Conversations": "Sohbetler",
    "Copy Link": "Bağlantıyı Kopyala", "Cost Price": "Maliyet Fiyatı",

    "Daily": "Günlük",
    "Date Created": "Oluşturulma Tarihi", "Date Modified": "Düzenleme Tarihi",
    "Default": "Varsayılan", "Define": "Tanımla", "Delete File": "Dosyayı Sil",
    "Description": "Açıklama", "Direct Message": "Doğrudan Mesaj",
    "Double-click to edit": "Düzenlemek için çift tıkla",
    "Drag & drop or click to select": "Sürükle bırak veya seçmek için tıkla",
    "Due": "Vade", "Due Date": "Vade Tarihi",

    "Editor": "Düzenleyici", "Email Subject": "E-posta Konusu",
    "Email me": "Bana e-posta gönder", "Empty": "Boş",
    "Enable": "Etkinleştir", "Enabled": "Etkin",
    "Enter": "Gir", "Enter description": "Açıklama gir",
    "Enter email": "E-posta gir", "Enter name": "Ad gir",
    "Enter password": "Parola gir", "Enter title": "Başlık gir",
    "Enter your email": "E-postanı gir", "Enter your name": "Adını gir",
    "Error": "Hata", "Event": "Etkinlik", "Events": "Etkinlikler",
    "Expand": "Genişlet", "Expense": "Gider", "Expenses": "Giderler",

    "Filter by": "Filtrele", "Final": "Son", "First": "İlk",
    "Folder": "Klasör", "Follow": "Takip Et", "Forgot password?": "Parolanı mı unuttun?",
    "From": "Kimden", "Full": "Tam",

    "Go back": "Geri dön", "Got it": "Anladım", "Group by": "Grupla",
    "High": "Yüksek", "History": "Geçmiş",
    "Icon": "Simge", "Image": "Görsel", "Images": "Görseller",
    "Income": "Gelir", "Income Statement": "Gelir Tablosu",
    "Information": "Bilgi", "Initial": "Başlangıç",
    "Integration": "Entegrasyon", "Invite": "Davet Et",
    "Invoice": "Fatura", "Invoices": "Faturalar",

    "Join": "Katıl", "Joined": "Katıldı",
    "Keep": "Tut", "Key": "Anahtar",
    "Last": "Son", "Last 7 days": "Son 7 gün", "Last 30 days": "Son 30 gün",
    "Last Month": "Geçen Ay", "Last Week": "Geçen Hafta", "Last Year": "Geçen Yıl",
    "Leave": "Çık", "Less": "Daha az", "Link": "Bağlantı",
    "Live": "Canlı", "Location": "Konum", "Logged in": "Giriş yapıldı",
    "Low": "Düşük",

    "Manage": "Yönet", "Manage Permissions": "İzinleri Yönet",
    "Manager": "Yönetici", "Mark all as read": "Tümünü okundu olarak işaretle",
    "Mark as read": "Okundu olarak işaretle", "Mark as unread": "Okunmadı olarak işaretle",
    "Material": "Malzeme", "Maybe later": "Belki sonra", "Medium": "Orta",
    "Member since": "Üyelik tarihi", "Mention": "Bahset", "Method": "Yöntem",
    "Mine": "Benim", "Modified": "Düzenlendi", "Monthly": "Aylık",
    "More": "Daha fazla", "More options": "Daha fazla seçenek",
    "Move": "Taşı", "Move to": "Taşı", "Multiple": "Çoklu",

    "Newest": "En yeni", "Next Page": "Sonraki Sayfa", "No file selected": "Dosya seçilmedi",
    "No items found": "Öğe bulunamadı", "No notifications": "Bildirim yok",
    "No record": "Kayıt yok", "No result": "Sonuç yok", "Not found": "Bulunamadı",
    "Notification": "Bildirim",

    "Off": "Kapalı", "On": "Açık", "Online": "Çevrimiçi", "Open": "Açık",
    "Operating": "Operasyon", "Optional": "İsteğe bağlı",
    "Order Date": "Sipariş Tarihi", "Order ID": "Sipariş No",
    "Order Items": "Sipariş Kalemleri", "Order list": "Sipariş listesi",
    "Order Status": "Sipariş Durumu", "Order Summary": "Sipariş Özeti",
    "Order Total": "Sipariş Toplamı", "Organization": "Organizasyon",
    "Overdue": "Gecikti", "Owner": "Sahip",

    "Page": "Sayfa", "Paid": "Ödendi", "Past Due": "Vadesi Geçti",
    "Payment": "Ödeme", "Payments": "Ödemeler", "Payment Method": "Ödeme Yöntemi",
    "Period": "Dönem", "Personal": "Kişisel", "Phone Number": "Telefon Numarası",
    "Pin": "Sabitle", "Pinned": "Sabitlendi", "Please wait...": "Lütfen bekle...",
    "Position": "Pozisyon", "Posted": "Yayımlandı", "Preview": "Önizleme",
    "Previous Page": "Önceki Sayfa", "Print Order": "Siparişi Yazdır",
    "Processing": "İşleniyor", "Profile Picture": "Profil Resmi",
    "Project": "Proje", "Public": "Herkese açık", "Purchase": "Satın Al",

    "Quantity Unit": "Adet Birimi", "Question": "Soru",
    "Read more": "Devamını oku", "Reason": "Sebep", "Receive": "Al",
    "Recent": "Son", "Recent Activity": "Son Etkinlikler", "Recent Orders": "Son Siparişler",
    "Reference": "Referans", "Refresh": "Yenile", "Region": "Bölge",
    "Reject": "Reddet", "Remove File": "Dosyayı Kaldır", "Replace": "Değiştir",
    "Reply": "Yanıtla", "Required": "Zorunlu", "Resend": "Tekrar Gönder",
    "Reset Password": "Parolayı Sıfırla", "Restore": "Geri Yükle",
    "Result": "Sonuç", "Results": "Sonuçlar", "Revenue": "Gelir",
    "Revenue Account": "Gelir Hesabı",

    "Sales Channel": "Satış Kanalı", "Sales Order": "Satış Siparişi",
    "Save & Close": "Kaydet ve Kapat", "Save Order": "Siparişi Kaydet",
    "Saving...": "Kaydediliyor...", "Schedule": "Planla", "Scheduled": "Planlandı",
    "Search...": "Ara...", "Search results": "Arama sonuçları", "Section": "Bölüm",
    "See all": "Tümünü gör", "See less": "Daha az göster", "See more": "Daha fazla göster",
    "Select": "Seç", "Select All": "Tümünü Seç", "Select Date": "Tarih Seç",
    "Select File": "Dosya Seç", "Select Files": "Dosyalar Seç",
    "Select Image": "Görsel Seç", "Select Option": "Seçenek Seç",
    "Send Message": "Mesaj Gönder", "Set": "Ayarla", "Share": "Paylaş",
    "Show": "Göster", "Show All": "Tümünü Göster", "Show More": "Daha Fazla Göster",
    "Sign in to your account": "Hesabına giriş yap", "Single": "Tekil",
    "Skip": "Atla", "Sort By": "Sırala",
    "Source": "Kaynak", "Start": "Başla", "Started": "Başladı",
    "Statistics": "İstatistikler", "Stock Level": "Stok Seviyesi",
    "Subject": "Konu", "Submit Order": "Siparişi Gönder", "Success": "Başarılı",
    "Summary": "Özet", "Support": "Destek", "Switch": "Değiştir",
    "System": "Sistem",

    "Tax Rate": "Vergi Oranı", "Team Tasks": "Takım Görevleri",
    "Templates": "Şablonlar", "Test": "Test", "This Month": "Bu Ay",
    "This Week": "Bu Hafta", "This Year": "Bu Yıl", "Time Zone": "Saat Dilimi",
    "Tip": "İpucu", "To": "Kime", "To Do": "Yapılacak",
    "Today's Tasks": "Bugünkü Görevler", "Today": "Bugün",
    "Tomorrow": "Yarın",
    "Total Amount": "Toplam Tutar", "Total Items": "Toplam Kalem",
    "Total Sales": "Toplam Satış", "Tracking": "Takip",
    "Type a message": "Bir mesaj yaz", "Type here": "Buraya yaz",

    "Unassigned": "Atanmamış", "Undo": "Geri Al", "Unit Price": "Birim Fiyat",
    "Unknown": "Bilinmiyor", "Unread": "Okunmamış", "Until": "Kadar",
    "Update Order": "Siparişi Güncelle", "Update Profile": "Profili Güncelle",
    "Updated by": "Güncelleyen", "Upload File": "Dosya Yükle",
    "Upload a file": "Dosya yükle", "Uploaded": "Yüklendi",
    "Use": "Kullan", "User": "Kullanıcı", "Users": "Kullanıcılar",

    "Verify": "Doğrula", "Version": "Sürüm", "View All": "Tümünü Görüntüle",
    "View Details": "Ayrıntıları Görüntüle", "View Profile": "Profili Görüntüle",
    "Visible": "Görünür",

    "Waiting": "Bekleniyor", "Warning": "Uyarı", "Website": "Web sitesi",
    "Weekly": "Haftalık", "Welcome": "Hoş geldin", "Welcome back": "Tekrar hoş geldin",
    "Yesterday": "Dün", "Yearly": "Yıllık",

    "Zip Code": "Posta Kodu", "Zoom": "Yakınlaştır",
}


def smart_translate(text):
    """Apply pattern-based fallback translations."""
    t = text.strip()
    if not t:
        return None

    # Skip JS template literals / code-like
    if "+" in t or "${" in t or "{{" in t:
        return None

    # Common prefixes
    if t.startswith("Add ") and not t.endswith("..."):
        rest = t[4:]
        return f"{rest} Ekle"
    if t.startswith("Edit "):
        rest = t[5:]
        return f"{rest}'yi Düzenle"
    if t.startswith("Delete "):
        rest = t[7:]
        return f"{rest}'yi Sil"
    if t.startswith("Create "):
        rest = t[7:]
        return f"{rest} Oluştur"
    if t.startswith("Save "):
        rest = t[5:]
        return f"{rest}'yi Kaydet"
    if t.startswith("Manage "):
        rest = t[7:]
        return f"{rest}'yi Yönet"
    if t.startswith("New "):
        rest = t[4:]
        return f"Yeni {rest}"
    if t.startswith("All "):
        rest = t[4:]
        return f"Tüm {rest}"
    if t.startswith("My "):
        rest = t[3:]
        return f"{rest}m" if rest.lower() in ("tasks", "orders", "products") else f"Benim {rest}"
    if t.startswith("View "):
        rest = t[5:]
        return f"{rest}'yi Görüntüle"
    if t.startswith("Search "):
        return f"{t[7:]} ara"

    return None


# Load .po, find EN-fallback entries, replace with TR
po = polib.pofile(r"C:/Users/enes3/erp/erp/locale/tr/LC_MESSAGES/django.po")

manual_added = 0
smart_added = 0
remaining = []
for entry in po:
    src = entry.msgid
    if not src:
        continue
    # If msgstr equals msgid, it's an EN fallback — try to translate
    if entry.msgstr == src:
        if src in EXTRA_TR:
            entry.msgstr = EXTRA_TR[src]
            manual_added += 1
        else:
            smart = smart_translate(src)
            if smart:
                entry.msgstr = smart
                smart_added += 1
            else:
                remaining.append(src)

# Make sure all EXTRA_TR entries exist in po
existing = {e.msgid for e in po}
for src, dst in EXTRA_TR.items():
    if src not in existing:
        po.append(polib.POEntry(msgid=src, msgstr=dst))
        manual_added += 1

po.save(r"C:/Users/enes3/erp/erp/locale/tr/LC_MESSAGES/django.po")
po.save_as_mofile(r"C:/Users/enes3/erp/erp/locale/tr/LC_MESSAGES/django.mo")
print(f"Manual TR added/updated: {manual_added}")
print(f"Smart-pattern TR added: {smart_added}")
print(f"Still EN-fallback (need pure manual TR later): {len(remaining)}")
print(f"Total .po entries: {len(po)}")
print()
if remaining[:25]:
    print("Sample remaining:")
    for s in remaining[:25]:
        print("  -", s)
