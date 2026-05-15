"""
One-shot script to build Turkish translations for current_account module.

Why we need this:
    `manage.py makemessages` requires GNU gettext (msguniq, msgfmt) which is not
    installed on this Windows box. Instead, we use polib to scan, dedupe, merge
    and compile .po/.mo files directly in Python.

What it does:
    1. Walks all templates (*.html) and python views in current_account/
    2. Extracts every `{% trans "X" %}`, `{% blocktrans %}...{% endblocktrans %}`,
       `_("X")`, `_g("X")`, `gettext("X")` literal string.
    3. Loads the existing locale/tr/LC_MESSAGES/django.po.
    4. For each extracted msgid, either keeps the existing translation or adds
       a new entry with our manual Turkish translation map below.
    5. Writes the updated .po and compiles to .mo.

Run with:
    python -m current_account._i18n_build
or:
    python current_account/_i18n_build.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import polib

# --------------------------------------------------------------------------
# Translation map — English (msgid) → Turkish (msgstr)
# --------------------------------------------------------------------------
TR = {
    # ---- Module headers ----
    "Current Account": "Cari Hesap",
    "Current Accounts": "Cari Hesaplar",
    "Accounts": "Cari Kartları",
    "ACCOUNTS": "CARİ KARTLARI",
    "All Accounts": "Tüm Cariler",
    "New Account": "Yeni Cari",
    "All Account": "Tüm Cari",
    "Account": "Cari",
    "Account List": "Cari Listesi",
    "Account Card": "Cari Kartı",
    "Account Movement": "Cari Hareketi",
    "Account Movements": "Cari Hareketleri",
    "Account Settings": "Cari Ayarları",
    "Edit Account": "Cari Düzenle",

    # ---- Invoice ----
    "Invoice": "Fatura",
    "Invoices": "Faturalar",
    "INVOICES": "FATURALAR",
    "All Invoices": "Tüm Faturalar",
    "New Invoice": "Yeni Fatura",
    "Edit Invoice": "Fatura Düzenle",
    "Invoice Item": "Fatura Kalemi",
    "Invoice Items": "Fatura Kalemleri",
    "Invoice Info": "Fatura Bilgisi",
    "Invoice Total": "Fatura Toplamı",
    "Invoice Allocations": "Fatura Eşleştirmeleri",
    "Sales Invoice": "Satış Faturası",
    "Purchase Invoice": "Alış Faturası",
    "Sales Return": "Satış İadesi",
    "Purchase Return": "Alış İadesi",
    "Proforma": "Proforma",
    "Issue Invoice": "Fatura Kes",
    "Save & Issue": "Kaydet & Kes",
    "Save as Draft": "Taslak Kaydet",
    "Issued": "Kesildi",
    "Linked Order": "Bağlı Sipariş",

    # ---- Payment ----
    "Payment": "Tahsilat / Ödeme",
    "Payments": "Tahsilatlar",
    "Collections / Payments": "Tahsilatlar / Ödemeler",
    "Collection / Payment": "Tahsilat / Ödeme",
    "COLLECTION / PAYMENT": "TAHSİLAT / ÖDEME",
    "All Payments": "Tüm Tahsilatlar",
    "New Collection / Payment": "Yeni Tahsilat / Ödeme",
    "New Collection": "Yeni Tahsilat",
    "Collection": "Tahsilat",
    "Payment Info": "Tahsilat Bilgisi",
    "Payment Amount": "Tahsilat Tutarı",
    "Payment Allocation": "Ödeme Eşleştirmesi",
    "Payment Allocations": "Ödeme Eşleştirmeleri",
    "Collection (from customer)": "Tahsilat (müşteriden)",
    "Payment (to supplier)": "Ödeme (tedarikçiye)",
    "Refund to Customer": "Müşteriye İade",
    "Refund from Supplier": "Tedarikçiden İade",
    "Save & Confirm": "Kaydet & Onayla",
    "Confirmed": "Onaylandı",
    "Applied to Invoices": "Faturalara Uygulanan",
    "Remaining as Advance": "Avans Olarak Kalan",
    "Allocated": "Eşleştirilen",
    "Applied": "Uygulanan",
    "Advance": "Avans",
    "Auto Match (FIFO)": "Otomatik Eşleştir (FIFO)",
    "ADVANCE (to account)": "AVANS (cari hesabına)",
    "Amount Distribution": "Tutar Dağılımı",
    "To Invoices": "Faturalara",
    "Open Invoices — Allocation": "Açık Faturalar — Eşleştirme",

    # ---- Check / PN ----
    "Check": "Çek",
    "Promissory Note": "Senet",
    "Check / Promissory Note": "Çek / Senet",
    "CHECK / PROMISSORY NOTE": "ÇEK / SENET",
    "Checks / Promissory Notes": "Çekler / Senetler",
    "Check / Promissory Note Portfolio": "Çek / Senet Portföyü",
    "New Check / Note": "Yeni Çek / Senet",
    "Portfolio": "Portföy",
    "Document Info": "Belge Bilgisi",
    "Document Details": "Belge Detayı",
    "Account & Direction": "Cari & Yön",
    "Amount & Dates": "Tutar & Tarihler",
    "Endorsed": "Ciro Edildi",
    "Endorsed To": "Ciro Edildi",
    "In Portfolio": "Portföyde",
    "Deposited to Bank": "Bankaya Verildi",
    "Cleared": "Tahsil Edildi",
    "Bounced": "Karşılıksız",
    "Returned": "İade Edildi",
    "Received from Customer": "Müşteriden Alınan",
    "Given to Supplier": "Tedarikçiye Verilen",
    "Came from customer": "Müşteriden geldi",
    "Given to supplier": "Tedarikçiye verildi",
    "Mark Bounced": "Karşılıksız İşaretle",
    "Deposit to Bank": "Bankaya Ver",
    "Endorse": "Ciro Et",
    "Endorse →": "Ciro Et →",
    "Clear": "Tahsil",
    "Cleared Cash Account": "Tahsil Edildiği Kasa",
    "Serial No": "Seri No",
    "Drawer": "Keşideci",
    "Bank": "Banka",
    "Bank / Drawer": "Banka / Keşideci",
    "Branch": "Şube",
    "Account No": "Hesap No",
    "Status Flow": "Durum Akışı",
    "Add to Portfolio": "Portföye Ekle",
    "Person who issued the check/note": "Çeki/senedi düzenleyen kişi",
    "Bank name (for checks)": "Çek için banka adı",
    "Internal note about this check/note...": "Bu çek/senetle ilgili iç not...",
    "Operation Status": "İşlem Durumu",
    "Out of Bank": "Bankadan Çıktı",
    "In Portfolio (given)": "Portföyde (verilen)",
    "Bounce notification": "Karşılıksız bildirim",
    "Received": "Alındı",
    "Given": "Verildi",
    "↓ Received": "↓ Alınan",
    "↑ Given": "↑ Verilen",
    "↓ Received from customer": "↓ Müşteriden alındı",
    "↑ Given to supplier": "↑ Tedarikçiye verildi",
    "Check + Note": "Çek + Senet",
    "All Directions": "Tüm Yönler",
    "Received in Portfolio": "Portföydeki Alınan",
    "Given in Portfolio": "Portföydeki Verilen",
    "Overdue in Portfolio": "Vadesi Geçen Portföydeki",

    # ---- Reports ----
    "Reports": "Raporlar",
    "REPORTS": "RAPORLAR",
    "Report Center": "Rapor Merkezi",
    "Account Reports": "Cari Raporları",
    "Aging": "Yaşlandırma",
    "Aging Report": "Yaşlandırma Raporu",
    "Aging analysis of open receivables and payables: 0-30, 30-60, 60-90, 90+ days": "Açık alacakların ve borçların yaşlanma analizi: 0-30, 30-60, 60-90, 90+ gün",
    "Trial Balance": "Cari Mizan",
    "Opening, debit, credit and closing balances of all accounts by book": "Defter bazlı tüm carilerin devir, borç, alacak, kapanış bakiyeleri",
    "Period filter available": "Dönem filtresi uygulanabilir",
    "Credit Limit": "Kredi Limiti",
    "Credit Limit Report": "Risk Limiti Raporu",
    "Customers reaching or exceeding their credit limit — accounts at risk": "Kredi limiti dolan ya da aşan müşteriler — risk altındaki cariler",
    "Credit limit usage for customers with a defined limit": "Kredi limiti tanımlı olan müşterilerin limit kullanım durumu",
    "Due Calendar": "Vade Takvimi",
    "Due Date Calendar": "Vade Takvimi",
    "Upcoming due dates — this week, next week, month-end and overdue": "Yaklaşan vadeler — bu hafta, gelecek hafta, ay sonu ve geçmiş vadeler",
    "Aging, trial balance, credit limit and due date calendar reports": "Yaşlandırma, mizan, risk limiti ve vade takvimi raporları",
    "No overdue invoices": "Vadesi geçen fatura yok",
    "No accounts exceeding the limit": "Limit aşan cari yok",
    "No upcoming due dates": "Yaklaşan vade yok",
    "Not Due": "Vadesi Gelmedi",
    "0-30 Days": "0-30 Gün",
    "30-60 Days": "30-60 Gün",
    "60-90 Days": "60-90 Gün",
    "90+ Days": "90+ Gün",
    "Overdue": "Vadesi Geçmiş",
    "This Week": "Bu Hafta",
    "Next Week": "Gelecek Hafta",
    "This Month (end)": "Bu Ay (sonu)",
    "Later": "Sonra",
    "Days Overdue (max)": "En Geç Gün",
    "Oldest Invoice": "En Eski Fatura",
    "Period": "Dönem",
    "Period Debit": "Dönem Borç",
    "Period Credit": "Dönem Alacak",
    "Total Opening": "Toplam Devir",
    "Total Closing": "Toplam Kapanış",
    "Total Debit": "Borç Toplamı",
    "Total Credit": "Alacak Toplamı",
    "Total Amount": "Toplam Tutar",
    "Total Collected": "Tahsilat Toplamı",
    "Total Paid": "Ödeme Toplamı",
    "Total Accounts": "Toplam Cari",
    "Total": "Toplam",
    "Filtered": "Filtrelenen",
    "Net Status": "Net Durum",
    "USD-based total": "USD tabanlı toplam",
    "+ : in our favor / − : against us": "+ : lehte / − : aleyhte",
    "Receivables (sales)": "Alacaklar (satış)",
    "Payables (purchases)": "Borçlar (alış)",
    "View": "Görünüm",
    "Only Exceeded": "Sadece Limit Aşanlar",
    "Near + Over Limit (80%+)": "Limit Yakın + Aşan (%80+)",
    "All Limited Accounts": "Tüm Limitli Cariler",
    "Limit Exceeded": "Limit Aşıldı",
    "Near Limit": "Limite Yaklaşıyor",
    "Usage": "Kullanım",
    "Remaining": "Kalan Limit",
    "No risks": "Risk bulunmuyor",
    "No customers exceeding limit.": "Limit aşan müşteri yok.",
    "No accounts match these criteria.": "Bu kriterlere uyan cari yok.",
    "Hide inactive": "Hareketsizleri gizle",
    "All accounts": "Tüm cariler",

    # ---- Common terms ----
    "Type": "Tip",
    "Types": "Tipler",
    "All Types": "Tüm Tipler",
    "Status": "Durum",
    "All Statuses": "Tüm Durumlar",
    "Direction": "Yön",
    "Method": "Yöntem",
    "Book": "Defter",
    "Books": "Defterler",
    "All Books": "Tüm Defterler",
    "Balance": "Bakiye",
    "All Balances": "Tüm Bakiyeler",
    "Amount": "Tutar",
    "Date": "Tarih",
    "Due Date": "Vade",
    "Due Date (optional)": "Vade (opsiyonel)",
    "Issue Date": "Düzenleme Tarihi",
    "Delivery Date": "Teslimat Tarihi",
    "Delivery": "Teslimat",
    "Movement Type": "Hareket Tipi",
    "Currency": "Para Birimi",
    "Cash Account": "Kasa Hesabı",
    "Cash Movement": "Kasa Hareketi",
    "Cash": "Nakit",
    "Bank Transfer / EFT": "Banka Havalesi / EFT",
    "Credit Card (POS)": "Kredi Kartı (POS)",
    "Offset": "Mahsup",
    "Other": "Diğer",
    "Description": "Açıklama",
    "Reference": "Referans",
    "Notes": "Notlar",
    "Name": "İsim",
    "Code": "Kod",
    "Email": "E-posta",
    "Phone": "Telefon",
    "Country": "Ülke",
    "City": "Şehir",
    "Billing Address": "Fatura Adresi",
    "Tax Office": "Vergi Dairesi",
    "Tax Info": "Vergi Bilgisi",
    "Tax No": "VKN",
    "Tax Number (VKN)": "VKN",
    "ID Number (TCKN)": "TCKN",

    # ---- Customer types ----
    "Customer": "Müşteri",
    "Supplier": "Tedarikçi",
    "Customer & Supplier": "Müşteri & Tedarikçi",
    "Staff": "Personel",

    # ---- Movement types ----
    "Opening Balance": "Açılış Bakiyesi",
    "Closing Balance": "Kapanış Bakiyesi",
    "Opening": "Devir",
    "Closing": "Kapanış",
    "Debit": "Borç",
    "Credit": "Alacak",
    "Debit (+)": "Borç (+)",
    "Credit (−)": "Alacak (−)",
    "Account now owes us": "Cari bize borçlandı",
    "Account paid / refunded": "Cari ödedi / iade aldı",
    "Advance Received": "Alınan Avans",
    "Advance Given": "Verilen Avans",
    "Interest / Late Fee": "Vade Farkı / Faiz",
    "Discount": "İskonto",
    "Discount Rate (%)": "İskonto Oranı (%)",
    "Offset / Adjustment": "Mahsup / Düzeltme",
    "Check/Note Received": "Çek/Senet Alındı",
    "Check/Note Given": "Çek/Senet Verildi",
    "Legacy - Receivable": "Eski Sistem - Alacak",
    "Legacy - Payable": "Eski Sistem - Borç",

    # ---- Invoice line items ----
    "Items": "Kalemler",
    "Invoice Items": "Fatura Kalemleri",
    "Quantity": "Miktar",
    "Unit": "Birim",
    "Unit Price": "Birim Fiyat",
    "Disc %": "İsk %",
    "VAT %": "KDV %",
    "VAT": "KDV",
    "Series": "Seri",
    "Other Charges": "Diğer Masraflar",
    "Subtotal": "Ara Toplam",
    "Grand Total": "Genel Toplam",
    "Open Balance": "Açık Bakiye",
    "Add Item": "Kalem Ekle",
    "Totals": "Toplamlar",

    # ---- Status labels ----
    "Draft": "Taslak",
    "Partially Paid": "Kısmi Ödendi",
    "Paid": "Ödendi",
    "Cancelled": "İptal",
    "Active": "Aktif",
    "Inactive": "Pasif",
    "All": "Tümü",
    "Owes Us": "Bize Borçlu",
    "We Owe": "Bizden Alacaklı",
    "Closed": "Kapalı",

    # ---- Form fields ----
    "Payment Term (days)": "Vade (gün)",
    "Opening Balance Date": "Açılış Tarihi",
    "Opening Date": "Açılış Tarihi",
    "Commercial Terms": "Ticari Koşullar",
    "Identity": "Kimlik",
    "Contact & Address": "İletişim & Adres",
    "Contact": "İletişim",
    "General Info": "Genel Bilgi",
    "Customer-specific discount": "Müşteriye özel iskonto",
    "+ owes us / − we owe": "+ bize borçlu / − bizden alacaklı",
    "Internal notes about this account...": "Bu cariye dair iç notlar...",
    "Invoice no, check no, etc.": "Fatura no, çek no, vs.",
    "What is this movement about?": "Bu hareket neyle ilgili?",
    "What is this payment / collection about?": "Bu tahsilat / ödeme neyle ilgili?",
    "Note about this invoice...": "Bu faturayla ilgili not...",
    "Internal note about this payment...": "Bu tahsilatla ilgili iç not...",

    # ---- CRM ----
    "CRM Link": "CRM Bağlantısı",
    "Recent Movements": "Son Hareketler",
    "Recent Invoices": "Son Faturalar",
    "Add Movement": "Hareket Ekle",
    "Issue Invoice": "Fatura Kes",
    "Receive Collection": "Tahsilat Al",
    "Statement": "Ekstre",
    "Check/Note": "Çek/Senet",
    "Current Balance": "Mevcut Bakiye",

    # ---- Buttons / actions ----
    "Filter": "Filtrele",
    "Save": "Kaydet",
    "Cancel": "İptal",
    "Delete": "Sil",
    "Edit": "Düzenle",
    "Print": "Yazdır",
    "Confirm": "Onayla",
    "Apply": "Uygula",
    "Save Movement": "Hareketi Kaydet",
    "Create Account": "Cari Oluştur",
    "Add to Portfolio": "Portföye Ekle",
    "Back": "Geri",
    "change": "değiştir",

    # ---- Search placeholders ----
    "Search: code, name, VKN, email, phone...": "Ara: kod, isim, VKN, e-posta, telefon...",
    "Search: invoice no, account, note...": "Ara: fatura no, cari, not...",
    "Search: payment no, account, description...": "Ara: tahsilat no, cari, açıklama...",
    "Search: serial no, bank, account, drawer...": "Ara: seri no, banka, cari, keşideci...",

    # ---- Select labels ----
    "Select Account": "Cari Seç",
    "— Select account —": "— Cari seç —",
    "— Select cash account —": "— Kasa seç —",
    "— Select —": "— Seç —",
    "— Select (optional) —": "— Seç (opsiyonel) —",

    # ---- Empty states ----
    "No accounts found": "Cari bulunamadı",
    "No invoices": "Fatura yok",
    "No payments": "Tahsilat yok",
    "No checks / notes": "Çek/Senet yok",
    "Adjust filters or open a new account.": "Filtreleri değiştir ya da yeni bir cari aç.",
    "Adjust filters or create a new invoice.": "Filtreleri değiştir ya da yeni bir fatura kes.",
    "Adjust filters or create a new payment.": "Filtreleri değiştir ya da yeni bir tahsilat oluştur.",
    "No instruments in the portfolio.": "Portföyde herhangi bir kıymetli evrak yok.",
    "No movements in the selected range.": "Seçilen aralıkta hareket yok.",
    "No movements in the selected period": "Seçilen dönemde hareket yok",
    "Adjust date range or book filter.": "Tarih aralığını ya da defter filtresini değiştir.",
    "Henüz hareket yok. Add the first movement": "Henüz hareket yok. İlk hareketi ekle",  # mixed if any

    # ---- Confirm dialogs ----
    "Are you sure you want to delete/deactivate this account?": "Bu cari kartını silmek/pasifleştirmek istediğine emin misin?",
    "Draft invoice will be deleted. Are you sure?": "Taslak fatura silinecek. Emin misin?",
    "Are you sure you want to cancel this invoice? A reverse movement will be created.": "Faturayı iptal etmek istediğine emin misin? Ters hareket oluşturulacak.",
    "Draft payment will be deleted. Are you sure?": "Taslak tahsilat silinecek. Emin misin?",
    "Payment will be cancelled, a reverse movement will be created. Are you sure?": "Tahsilat iptal edilecek, ters hareket oluşturulacak. Emin misin?",
    "Check will be marked as bounced. A reverse movement will be written on the account. Are you sure?": "Çek karşılıksız olarak işaretlenecek. Cari hesaba ters hareket yazılacak. Emin misin?",
    "Check will be cancelled. All account movements will be reversed. Are you sure?": "Çek iptal edilecek. Tüm cari hareketleri tersine alınacak. Emin misin?",
    "Will be cancelled. Are you sure?": "İptal edilecek. Emin misin?",

    # ---- Statement / Ekstre ----
    "Statement —": "Ekstre —",
    "From": "Başlangıç",
    "To": "Bitiş",

    # ---- Movement / Payment ----
    "New Movement": "Yeni Hareket",
    "Movement added.": "Hareket eklendi.",
    "Open invoices will load after selecting an account.": "Cari'yi seçince açık faturalar yüklenir.",
    "No open invoices — payment will be recorded as advance.": "Açık fatura yok — tahsilat avans olarak girecek.",
    "Select which invoices to apply this payment to. Any unallocated amount is recorded as an advance on the account.": "Tahsilatın hangi faturalara uygulanacağını seç. Eşleştirilmeyen kısım avans olarak cari hesaba yazılır.",

    # ---- Sidebar (page chrome) ----
    "HELP": "YARDIM",
    "Help": "Yardım",
    "User Guide": "Kullanım Kılavuzu",

    # ---- Misc ----
    "Summary": "Özet",
    "Amount Distribution": "Tutar Dağılımı",
    "Tracks the status of checks and promissory notes received from customers and given to suppliers": "Müşterilerden alınan ve tedarikçilere verilen çek/senetlerin durum takibi",
    "Customer collections and supplier payments": "Müşteri tahsilatları ve tedarikçi ödemeleri",
    "All sales / purchase / return / proforma invoices": "Tüm satış / alış / iade / proforma faturaları",
    "Unified view of customer and supplier accounts, balances, and movements": "Müşteri ve tedarikçilerin birleşik kart görünümü, bakiyeleri ve hareketleri",

    # ---- Sort options ----
    "Name (A→Z)": "İsim (A→Z)",
    "Name (Z→A)": "İsim (Z→A)",
    "Code (asc)": "Kod (artan)",
    "Balance (high→low)": "Bakiye (büyük→küçük)",
    "Balance (low→high)": "Bakiye (küçük→büyük)",
    "Most Recent": "En Son Hareket",

    # ---- Balance filters ----
    "Positive (Owes Us)": "Bize Borçlu",
    "Negative (We Owe)": "Bizden Alacaklı",

    # ---- View messages ----
    "Book and currency are required.": "Defter ve para birimi zorunludur.",
    "Account created: %(code)s": "Cari oluşturuldu: %(code)s",
    "Account updated.": "Cari kartı güncellendi.",
    "Invalid amount.": "Geçersiz tutar.",
    "Amount cannot be zero.": "Tutar sıfır olamaz.",
    "An account must be selected.": "Cari seçilmelidir.",
    "You must add at least one invoice item.": "En az bir fatura kalemi eklemelisin.",
    "Invoice created: %(label)s": "Fatura oluşturuldu: %(label)s",
    "Invoice updated.": "Fatura güncellendi.",
    "Invoice cancelled.": "Fatura iptal edildi.",
    "Payment created: %(number)s": "Tahsilat oluşturuldu: %(number)s",
    "Payment cancelled.": "Tahsilat iptal edildi.",
    "Check endorsed to %(name)s.": "Çek %(name)s cariye ciro edildi.",
    "Check marked as bounced.": "Çek karşılıksız olarak işaretlendi.",
    "Check cancelled.": "Çek iptal edildi.",
    "Check marked as deposited to bank.": "Çek bankaya verildi olarak işaretlendi.",
    "Items must be a list.": "Kalemler bir liste olmalı.",
    "Allocations must be a list.": "Eşleştirmeler bir liste olmalı.",
    "Amount must be greater than zero.": "Tutar sıfırdan büyük olmalı.",
    "A cash account must be selected.": "Kasa hesabı seçilmelidir.",
    "An account to endorse to must be selected.": "Ciro edilecek cari seçilmelidir.",
    "Only draft invoices can be edited.": "Yalnızca taslak faturalar düzenlenebilir.",
    "Only draft invoices can be deleted. Cancel issued invoices instead.": "Yalnızca taslak faturalar silinebilir. Kesilmiş faturayı iptal et.",
    "Only draft payments can be deleted. Cancel confirmed payments instead.": "Yalnızca taslak tahsilatlar silinebilir. Onaylanmışsa iptal et.",

    # ---- Help page key sections ----
    "User Guide": "Kullanım Kılavuzu",
    "Quick Start (in 5 minutes)": "Hızlı Başlangıç (5 dakikada)",
    "Quick Start": "Hızlı Başlangıç",
    "Daily Scenarios": "Günlük Senaryolar",
    "Core Concepts": "Temel Kavramlar",
    "FAQ": "SSS",
    "Contents": "İçindekiler",
    "Movements": "Hareketler",
    "Movement": "Hareket",
    "First 3 steps": "İlk 3 adım",
}


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
APP_ROOT = Path(__file__).resolve().parent
LOCALE_PO = APP_ROOT.parent / "locale" / "tr" / "LC_MESSAGES" / "django.po"
LOCALE_MO = APP_ROOT.parent / "locale" / "tr" / "LC_MESSAGES" / "django.mo"


# Extraction patterns
PATTERNS = [
    re.compile(r"""\{%\s*trans\s+["'](?P<s>[^"']+)["']\s*%\}"""),
    re.compile(r"""\{%\s*blocktrans[^%]*%\}(?P<s>.*?)\{%\s*endblocktrans\s*%\}""", re.DOTALL),
    re.compile(r"""\b_\(\s*["'](?P<s>[^"']+)["']\s*\)"""),
    re.compile(r"""\b_g\(\s*["'](?P<s>[^"']+)["']\s*\)"""),
    re.compile(r"""\bgettext\(\s*["'](?P<s>[^"']+)["']\s*\)"""),
    re.compile(r"""\bgettext_lazy\(\s*["'](?P<s>[^"']+)["']\s*\)"""),
]


def extract_strings_from_file(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()
    found = set()
    for pat in PATTERNS:
        for m in pat.finditer(text):
            s = m.group("s").strip()
            if s:
                found.add(s)
    return found


def collect_all() -> set[str]:
    out = set()
    # Walk templates in current_account/
    for p in APP_ROOT.glob("templates/**/*.html"):
        out |= extract_strings_from_file(p)
    # Walk python source
    for p in APP_ROOT.glob("*.py"):
        if p.name.startswith("_"):
            continue
        out |= extract_strings_from_file(p)
    # Also include the sidebar files + base.html (they reference current_account URLs)
    project_root = APP_ROOT.parent      # c:/.../erp (Django project)
    repo_root    = project_root.parent  # c:/.../  (repo root)
    extra_files = [
        project_root / "erp" / "templates" / "base.html",
        project_root / "erp" / "templates" / "components" / "_sidebar_nejum.html",
        repo_root / "templates" / "themes" / "nejum" / "components" / "_sidebar_nejum.html",
    ]
    for p in extra_files:
        if p.exists():
            out |= extract_strings_from_file(p)
        else:
            print(f"  WARN: extra file not found: {p}")
    return out


def main():
    print(f"Loading {LOCALE_PO}...")
    po = polib.pofile(str(LOCALE_PO))
    existing_ids = {e.msgid for e in po}
    print(f"  Existing entries: {len(po)}")

    new_strings = collect_all()
    print(f"  Found in current_account: {len(new_strings)} strings")

    added = 0
    updated = 0
    overridden = 0
    for msgid in sorted(new_strings):
        translation = TR.get(msgid)
        existing = next((e for e in po if e.msgid == msgid), None)

        if existing:
            if translation and existing.msgstr != translation:
                # Override existing translation with our preferred Turkish
                existing.msgstr = translation
                if not existing.msgstr:
                    updated += 1
                else:
                    overridden += 1
            elif not existing.msgstr and translation:
                existing.msgstr = translation
                updated += 1
        else:
            new = polib.POEntry(msgid=msgid, msgstr=translation or "")
            po.append(new)
            added += 1

    print(f"  Added: {added}, Updated (was blank): {updated}, Overridden (existing): {overridden}")

    # Save .po
    po.save(str(LOCALE_PO))
    print(f"  Saved .po -> {LOCALE_PO}")

    # Compile .mo
    po.save_as_mofile(str(LOCALE_MO))
    print(f"  Compiled .mo -> {LOCALE_MO}")

    # Sanity check: count entries with non-empty msgstr that came from our TR map
    translated_count = sum(1 for e in po if e.msgstr and not e.fuzzy)
    print(f"  Total translated entries in .po: {translated_count}/{len(po)}")


if __name__ == "__main__":
    main()
