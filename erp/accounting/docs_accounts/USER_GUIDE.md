# Cari Hesap Modülü — Kullanım Kılavuzu

> ByteEntegre / Logo tarzı klasik **cari hesap** modülü. Müşteri-tedarikçi kartları, faturalar, tahsilat-ödemeler, çek-senet ve raporlar bir arada.

---

## İçindekiler

1. [Hızlı Başlangıç (5 dakika)](#1-hızlı-başlangıç-5-dakika)
2. [Günlük Senaryolar](#2-günlük-senaryolar)
3. [Temel Kavramlar](#3-temel-kavramlar)
4. [Cari Kartı](#4-cari-kartı)
5. [Faturalar](#5-faturalar)
6. [Tahsilat / Ödeme](#6-tahsilat--ödeme)
7. [Çek / Senet](#7-çek--senet)
8. [Raporlar](#8-raporlar)
9. [SSS](#9-sss)

---

## 1. Hızlı Başlangıç (5 dakika)

### Modülün özeti
Sistem **her müşteri ve tedarikçi için tek bir Cari Hesap kartı** açar (örnek kod: `CARI-001`). Bu kartın altında:

- **Hareketler** (movements) — her finansal etki bir satır (fatura, tahsilat, ciro, vs.)
- **Bakiye** — hareketlerin toplamı, otomatik
- **Faturalar** — bu cariye kesilmiş tüm satış/alış faturaları
- **Tahsilatlar / Ödemeler** — paranın el değiştirdiği işlemler
- **Çekler / Senetler** — portföyde bekleyen kıymetli evraklar

### İlk 3 adım

1. **Cari kartı aç:** `/cari/yeni/` — müşteri ya da tedarikçi seç, varsa eski açılış bakiyesini gir.
2. **Fatura kes:** Cari sayfasında **"Fatura Kes"** mor butonu → kalemleri ekle → "Kaydet & Kes".
3. **Tahsilat al:** Cari sayfasında **"Tahsilat Al"** yeşil butonu → açık faturalar otomatik listelenir, eşleştir.

Hepsi bu. Bakiye, ekstre, durum güncellenir.

---

## 2. Günlük Senaryolar

### Senaryo A — Müşteriye satış yapıyorum, sonra parayı alıyorum

1. **Cari aç** *(zaten varsa atla)*: `/cari/yeni/` → "Yeni müşteri"
2. **Satış faturası kes**: Cari detay sayfasında → **"Fatura Kes"** → Tip: *Satış Faturası*
   - Kalemleri ekle (her satırda KDV oranı vardır)
   - **"Kaydet & Kes"** tıkla → cari bakiyesi otomatik artar (cari sana borçlanmış olur)
3. **Müşteri ödemesini yaptığında**: Cari sayfasında → **"Tahsilat Al"**
   - Açık faturalar otomatik listelenir
   - **"Otomatik Eşleştir (FIFO)"** butonuyla en eski fatura(lar)ı kapatır
   - Ya da manuel olarak hangi faturaya ne kadar uygulanacağını gir
   - Kasayı seç → **"Kaydet & Onayla"**
4. **Sonuç**:
   - Fatura durumu: `Ödendi` ya da `Kısmi Ödendi`
   - Cari bakiyesi: kapanır ya da azalır
   - Kasa: para girişi kaydedildi

### Senaryo B — Tedarikçiden mal aldım, ödeme yapacağım

1. **Cari aç**: Tip = `Tedarikçi`
2. **Alış faturası**: Cari → "Fatura Kes" → Tip: *Alış Faturası*
   - Cari bakiyesi negatif olur (sen onlara borçlanmış olursun)
3. **Ödeme**: Cari → "Tahsilat Al" → Tip: *Ödeme (tedarikçiye)*
   - Tutar gir, kasadan düşülecek hesabı seç
   - Faturayı kapat
4. **Sonuç**: Cari bakiyesi sıfıra döner, kasa azalır.

### Senaryo C — Müşteri çek getirdi

1. **Çek girişi**: `/cari/cek-senet/yeni/` → Yön: *Alınan*
   - Banka, seri no, vade tarihi, tutar gir
   - **"Portföye Ekle"** tıkla
2. **Otomatik etki**: Cari bakiyesi azalır (sanki tahsilat almışsın gibi) — çünkü müşteri sana çek vermiş, borcunun yerini kıymetli evrak almıştır.
3. **Vade geldiğinde 3 seçenek var** — Çek detay sayfasında sağdaki aksiyon panelinden:
   - **Bankaya Ver** → durum: *Bankaya Verildi* (henüz para yok)
   - **Tahsil Et** → kasa seç → para girer, durum: *Tahsil Edildi*
   - **Ciro Et** → başka cariye devret (örnek: tedarikçiye verirsin)
4. **Karşılıksız çıkarsa**: **"Karşılıksız İşaretle"** → cari'ye **ters hareket (+X)** yazılır, alacak geri açılır.

### Senaryo D — Müşteri ekstresini istedi

Cari detay sayfasında → **"Ekstre"** butonu → Tarih aralığı seç → **"Yazdır"**.
PDF gibi temiz, devir-borç-alacak-kapanış kolonlarıyla profesyonel çıktı.

### Senaryo E — "Kim bana borçlu, ne kadar gecikmiş?"

`/cari/rapor/yaslandirma/` → Tüm açık alacaklar `0-30 / 30-60 / 60-90 / 90+ gün` kovalarına bölünür. Cari başına ve toplam görürsün.

### Senaryo F — "Hangi faturanın vadesi yakın?"

`/cari/rapor/vade-takvimi/` → `Vadesi Geçmiş / Bu Hafta / Gelecek Hafta / Bu Ay / Sonra` gruplarında listeler.

### Senaryo G — Kredi limiti olan müşteri kontrolü

1. Cari kartını düzenle → **Kredi Limiti** alanına bir tutar gir (örnek: 10.000)
2. `/cari/rapor/risk-limiti/` → limit kullanım yüzdesi olan tüm müşteriler
3. %80 + aşan müşteriler "Limite Yaklaşıyor" / "Limit Aşıldı" rozeti alır

---

## 3. Temel Kavramlar

### İşaret kuralı (sign convention)

Sistemin kalbi tek bir kural üstüne kurulu:

| `CariMovement.amount` | Anlam |
|---|---|
| **Pozitif (+)** | Cari **bize borçlu** / biz alacaklıyız |
| **Negatif (−)** | **Biz cariye borçluyuz** / cari bize ödedi |
| **0** | Hesap kapalı |

Aynı kural `CariAccount.cached_balance`'a da uygulanır. Cari kartında **"Bize Borçlu"** ya da **"Bizden Alacaklı"** etiketi otomatik gelir.

### Hareket → Bakiye

Bakiye depolanan bir alan değil, hareketlerin toplamıdır:

```
Bakiye = SUM(CariMovement.amount) WHERE cari = X
```

Bu yüzden:
- Hareketi sildiğinde / değiştirdiğinde bakiye otomatik düzelir
- Eski accounting tablolarındaki dağınık kayıtlar bile mantıklı bir bakiye verir
- İptal işlemi orijinal satırı silmez, **ters hareket** yazar (audit-safe)

### Durum (status) akışları

**Fatura:**
```
taslak → kesilmiş → kısmi ödendi → ödendi
                 └─→ iptal
```

**Tahsilat:**
```
taslak → onaylandı
       └─→ iptal
```

**Çek/Senet (alınan):**
```
portföyde ──┬─► bankaya verildi ──► tahsil edildi
            ├─► tahsil edildi
            ├─► ciro edildi
            └─► karşılıksız / iptal
```

### Cari kodu

Her defter (`Book`) bağımsız bir sayaç tutar:
- `CARI-001`, `CARI-002`, ... sırasıyla otomatik atanır
- İki ayrı defterde aynı kod olabilir (örneğin defter A'da CARI-001, defter B'de de CARI-001) — kod **(book, code)** kombinasyonu olarak unique
- Manuel kod girmek istemiyorsan boş bırak, otomatik atanır

### Defter (Book) ayrımı

Her cari, fatura, tahsilat ve çek bir **defter**e bağlıdır. Bu çoklu işletme/yan kuruluş senaryoları için. Tek işletmen varsa tek defter yeterli.

### Multi-currency

- Her hareket kendi para biriminde (`currency`) tutulur
- Aynı zamanda **base currency** (USD)'ye normalize edilmiş `amount_base` da saklanır
- Mizan ve yaşlandırma raporları base currency'de birikir
- Kur, hareket tarihindeki ratesi (`accounting.services.get_exchange_rate`) ile alınır

---

## 4. Cari Kartı

### Açma

`/cari/yeni/` veya sidebar → **Cari Kartı → Yeni Cari**

**Zorunlu alanlar:**
- İsim
- Tip (Müşteri / Tedarikçi / İkisi / Personel / Diğer)
- Defter
- Para birimi

**Önerilen alanlar (vergi & risk):**
- Vergi dairesi, VKN, TCKN (e-Arşiv'e hazır)
- Vade gün sayısı (varsayılan: 30)
- Kredi limiti (0 = limitsiz)
- Açılış bakiyesi (+ : bize borçlu / − : bizden alacaklı)

### CRM bağlantısı

Cari isteğe bağlı olarak `crm.Contact`, `crm.Company` veya `crm.Supplier`'dan birine bağlanır. Aynı CRM kaydı için aynı defterde sadece bir cari açılabilir (DB seviyesinde kısıtlanır).

### Düzenleme / Pasifleştirme

- "Düzenle" butonu — tüm alanlar güncellenebilir
- "Sil" butonu — eğer cari'nin hareketleri varsa silinmez, **pasifleştirilir** (`is_active=False`)
- Tamamen silmek için önce tüm hareketleri silmelisin (önerilmez)

---

## 5. Faturalar

### Tipler

| Tip | Anlam | Cari hareketi |
|---|---|---|
| **Satış Faturası** | Müşteriye düzenlediğin | +Total |
| **Alış Faturası** | Tedarikçiden gelen | −Total |
| **Satış İadesi** | Müşteriden iade aldın | −Total |
| **Alış İadesi** | Tedarikçiye iade ettin | +Total |
| **Proforma** | Bağlayıcı olmayan teklif | Hareket yok |

### Kesim akışı

1. **Taslak oluştur**: Kalemleri eklersin, KDV satır bazında hesaplanır
2. **"Kes"**: Statü `kesilmiş` olur, `CariMovement` otomatik yaratılır, bakiye güncellenir
3. **"İptal"** (kesilmişse): Ters `CariMovement` yazılır, orijinal silinmez

> Taslak halindeki fatura cari hesabı etkilemez. Kestiğin an etkiler.

### KDV ve iskonto

Her satırda ayrı tanımlanır:
- **İskonto %**: önce uygulanır (satır toplamından düşer)
- **KDV %**: iskonto sonrası net üzerine eklenir
- Aynı faturada farklı KDV oranları olabilir (örnek: bazı kalemler %20, bazıları %10)
- Detay sayfasında **KDV breakdown** otomatik gösterilir

### Diğer masraflar

Nakliye, paketleme gibi ek tutarlar fatura genelinde `other_charges` alanına girilir. KDV uygulanmaz, doğrudan toplama eklenir.

### Düzenleme

Sadece **taslak** faturalar düzenlenebilir. Kesim sonrası fatura "donar" — düzenlemek için iptal edip yeniden kesmelisin.

---

## 6. Tahsilat / Ödeme

### 4 tip

| Tip | Anlam | Cari etkisi | Kasa etkisi |
|---|---|---|---|
| **Tahsilat (müşteriden)** | Müşteri sana ödedi | − | + |
| **Ödeme (tedarikçiye)** | Sen tedarikçiye ödedin | + | − |
| **Müşteriye İade** | Sen müşteriye geri verdin | + | − |
| **Tedarikçiden İade** | Tedarikçi sana geri verdi | − | + |

### Ödeme yöntemleri

Nakit / Banka Havalesi / EFT / Kredi Kartı / Çek / Senet / Mahsup / Diğer.
**Çek/senet seçtiysen** ayrıca `/cari/cek-senet/` üzerinden o belgeyi de kaydetmen önerilir.

### Açık fatura eşleştirme

Tahsilat oluştururken cariyi seçtiğinde, o carinin tüm açık faturaları (statü `kesilmiş` veya `kısmi ödendi`) tabloda gelir.

- **Otomatik Eşleştir (FIFO)**: tutarın yetebildiği kadar eski faturaları kapatır
- **Manuel**: Her faturaya ne kadar uygulanacağını sen yazarsın
- **Avans**: Eşleştirilmeyen kısım otomatik olarak `invoice=NULL` kaydı olur, cari hesabında avans gibi durur (sonraki faturada kullanılabilir)

### Onaylama

Tahsilat **draft** durumunda iken cari ve kasa etkilenmez. **"Kaydet & Onayla"** ya da sonradan **"Onayla"** ile gerçek hesap güncellenir.

### İptal

Onaylanmış tahsilat iptal edildiğinde:
- Ters `CariMovement` yazılır
- Kasa balanced edilir (F('balance') - delta)
- Eşleştirilen faturalar otomatik `kesilmiş` durumuna döner

---

## 7. Çek / Senet

### Yön ve durum

**Yön (direction):**
- **Alınan**: Müşteriden geldi — portföyde tutarsın
- **Verilen**: Tedarikçiye verdin — sen kıymetli evrak ile borcunu kapattın

**Durumlar:**
- `Portföyde` — elinde
- `Bankaya Verildi` — tahsile gönderildi, henüz para gelmedi
- `Tahsil Edildi` — kasaya girdi (alınan) ya da çıktı (verilen)
- `Ciro Edildi` — başka cariye devredildi
- `Karşılıksız` — bounce
- `İade Edildi` / `İptal`

### Aksiyon panelinden ne yapabilirim?

| Mevcut durum | Yapılabilir |
|---|---|
| Portföyde (alınan) | Bankaya Ver / Tahsil / Ciro / Karşılıksız / İptal |
| Portföyde (verilen) | Tahsil / İptal |
| Bankaya Verildi | Tahsil / Karşılıksız / İptal |
| Tahsil/Ciro/Karşılıksız/İptal | Yeni işlem yok |

### Ciro etmek

Müşterinden aldığın çeki tedarikçine verirsin. Sistem:
1. Çek statüsünü `Ciro Edildi` yapar, `endorsed_to` alanına hedef cariyi yazar
2. Hedef cari'ye **+X CariMovement** yazar (sanki onlara ödeme yapmışsın gibi — onların alacağı azalır)
3. Orijinal hareket durur (müşterinden alma hâlâ geçerli)

### Karşılıksız (bounce)

Hayat gerçeği: bazen çek geri döner.
- Statü → `Karşılıksız`
- Müşterinin cari hesabına **+X CariMovement** yazılır (alacağın yeniden açılır)
- Daha sonra ne yapacağın senin elinde: yasal takip, anlaşma, vs.

---

## 8. Raporlar

`/cari/rapor/` → 4 büyük rapor

### Yaşlandırma (Aging)

- Açık alacakları / borçları `0-30 / 30-60 / 60-90 / 90+ gün` kovalarına böler
- Cari başına ve toplam tablo
- "En geç gün" rozeti her satırda — kırmızılaşır vade arttıkça
- Tip filtresi: alacaklar (satış) ↔ borçlar (alış)

### Cari Mizan (Trial Balance)

Klasik mizan tablosu:
- **Devir** (dönem başı bakiye)
- **Borç** (dönem içi pozitif hareketler)
- **Alacak** (dönem içi negatif hareketler)
- **Kapanış** (dönem sonu bakiye)

Filtreler:
- Tarih aralığı (varsayılan: yıl başından bugüne)
- Defter
- Hareketsiz cariler gizle / göster

### Risk Limiti (Credit Limit)

Kredi limiti tanımlı tüm müşterilerin kullanım oranını gösterir:
- Görsel **progress bar** (yeşil/sarı/kırmızı)
- "Sadece Limit Aşanlar" / "%80+ ve aşan" / "Tümü"
- Kalan limit, % kullanım, bakiye

### Vade Takvimi

Açık faturalar şu gruplarda:
- 🔴 Vadesi Geçmiş
- 🟡 Bu Hafta
- 🔵 Gelecek Hafta
- 🟣 Bu Ay (sonu)
- ⚪ Sonra

Her grup içinde fatura numarası, cari, kalan tutar görünür. Her fatura tek tıkla detayına gider.

---

## 9. SSS

### Yanlış fatura kestim, ne yapacağım?

**Taslak ise**: "Sil" butonu — temiz silinir.
**Kesilmişse**: "İptal Et" — ters cari hareketi otomatik yazılır, orijinal kayıt kalır (audit-safe). Sonra doğrusunu yeni fatura olarak kes.

### Tahsilat yanlış girdim?

Aynı mantık: onaylanmamışsa sil, onaylanmışsa iptal et. İptal her şeyi geri alır (cari, fatura statüsü, kasa).

### Aynı müşteri için iki cari kartı açtım?

Sistem aynı CRM kaydı (Contact/Company/Supplier) için aynı defterde iki cari engelliyor. Ama isim olarak benzer iki kart açtıysan elle birleştirmen gerekir (Faz 6'da merge tool gelebilir).

### Müşterimi tedarikçi olarak da kullanıyorum — iki ayrı cari mi açmalıyım?

Hayır. Cari tipini **"Müşteri & Tedarikçi"** olarak işaretle. Tüm hareketler tek kartta toplanır, bakiye otomatik nettir.

### Açılış bakiyesini sonradan değiştirebilir miyim?

Doğrudan değil ama eşdeğeri: cari kartında **"Hareket Ekle"** ile pozitif/negatif bir `adjustment` hareketi gir, açıklamasına "Açılış düzeltmesi" yaz.

### Eski accounting modülümdeki Alacaklar/Borçlar ne oldu?

Hepsi **otomatik** olarak Cari kartlarına taşındı (Faz 1 migration). Eski tablolar (`AssetAccountsReceivable`, `LiabilityAccountsPayable`) hâlâ duruyor ve yeni cari hareketleri otomatik onlara da yazılıyor (signals). Eski dashboard'larını bozmadık.

### Ekstre PDF olarak alabilir miyim?

Browser'ın yazdır fonksiyonu (Ctrl+P) → "PDF olarak kaydet". Sayfa `@media print` ile optimize edilmiş, butonlar ve filtreler otomatik gizleniyor.

### Bir tahsilatı birden fazla faturaya bölebilir miyim?

Evet. Tahsilat formunda eşleştirme tablosunda her faturaya istediğin tutarı yazarsın, ya da "Otomatik Eşleştir (FIFO)" en eski faturaları sırayla kapatır.

### Tahsilatın bir kısmı avans olarak kalabilir mi?

Evet. Tahsilat tutarı eşleştirmelerin toplamından büyükse fark otomatik **avans** olarak kaydedilir (`invoice=NULL`). Sonraki bir faturada bu avansı kullanabilirsin (Faz 6'da explicit "avansı uygula" butonu gelebilir).

### Çek bankaya verdim, ne zaman kasaya işler?

Bankaya verme sadece statü değişimi (`Bankaya Verildi`). Para gerçekten geldiğinde **"Tahsil Et"** ile kasa hesabını seçersin, ancak o zaman kasa balance'ı artar.

### Multi-tenant / ENV_PROFILE — bu modül desteklemiyor mu?

Destekler. Her `Book` ayrı bir işletme/marka gibi davranır. ENV_PROFILE değişip schema değiştiğinde tüm cariler/hareketler/faturalar/çekler izole kalır.

---

## Mimari Notlar (Geliştiriciler için)

### Modeller

| Model | Görev |
|---|---|
| `CariAccount` | Tek kart per müşteri/tedarikçi (book bazlı unique) |
| `CariMovement` | Atomik ledger satırı, bakiye = SUM(amount) |
| `CariSettings` | Defter bazlı sayaçlar (next_cari_seq, next_invoice_seq, next_payment_seq) |
| `Invoice` + `InvoiceItem` | Faturalar, KDV satır bazında |
| `Payment` + `PaymentAllocation` | Tahsilat ve fatura eşleştirmesi |
| `CheckOrPromissoryNote` | Çek/senet portföyü, state machine |

### Eski accounting ile sync

`signals.py` her `CariMovement` post_save'inde:
- `amount > 0` → `AssetAccountsReceivable` yazar/günceller
- `amount < 0` ve cari.supplier var → `LiabilityAccountsPayable` yazar/günceller

Geri yönde sync yok (tek yönlü mirror). Yeni iş Cari'den akar, eski sistem sadece okur.

### Migration sırası

1. `0001_initial` — temel modeller
2. `0002_backfill_from_legacy_ar_ap` — mevcut AR/AP'i otomatik aktarır (idempotent)
3. `0003_invoice_invoiceitem_and_more`
4. `0004_payment_paymentallocation_and_more`
5. `0005_checkorpromissorynote`

### URL yapısı

```
/cari/                              # Cari listesi
/cari/<id>/                         # Cari detayı (özet + son hareketler + son faturalar)
/cari/<id>/ekstre/                  # Ekstre (PDF-ready)
/cari/fatura/                       # Fatura listesi
/cari/tahsilat/                     # Tahsilat listesi
/cari/cek-senet/                    # Çek/senet portföyü
/cari/rapor/                        # Rapor merkezi
/cari/rapor/yaslandirma/
/cari/rapor/mizan/
/cari/rapor/risk-limiti/
/cari/rapor/vade-takvimi/
```

### Test komutu

```python
# Cari modülünün sağlığını kontrol et
from current_account.models import CariAccount
from django.db.models import Sum

for c in CariAccount.objects.all():
    mv_sum = c.movements.aggregate(s=Sum("amount"))["s"] or 0
    if abs(c.cached_balance - mv_sum) > 0.01:
        print(f"MISMATCH {c.code}: cached={c.cached_balance} sum={mv_sum}")
```

Sıfır mismatch → tüm bakiyeler tutarlı.
