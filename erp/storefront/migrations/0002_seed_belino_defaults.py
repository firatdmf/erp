"""
Mevcut Belino sitesindeki hardcoded NAV ve SEASONS verisini DB'ye taşır
ki ERP'ye geçişte site GÖRSEL OLARAK bozulmasın. Tek değişiklik:
artık içerik DB'den geliyor, kod değil.

Bu migration sadece BELINO storefront yoksa veri yaratır → idempotent.
"""
from django.db import migrations


# Belino Header.tsx'teki NAV array'inin birebir yansıması.
NAV_ITEMS = [
    {
        "label_tr": "Çorap", "label_en": "Socks", "order": 0,
        "feature_title": "Pamuklu klasik soket",
        "feature_meta": "12'li paket · %85 pamuk",
        "feature_image_url": "/home/hero-c.png",
        "children": [
            {"label_tr": "Erkek çorap",  "label_en": "Men",      "swatch": "#0E0E0C", "href": "/products?cat=erkek-corap"},
            {"label_tr": "Kadın çorap",  "label_en": "Women",    "swatch": "#B8654A", "href": "/products?cat=kadin-corap"},
            {"label_tr": "Çocuk çorabı", "label_en": "Kids",     "swatch": "#5C7C6F", "href": "/products?cat=cocuk-corap"},
            {"label_tr": "Bebek çorabı", "label_en": "Baby",     "swatch": "#E9C7B8", "href": "/products?cat=bebek-corap"},
            {"label_tr": "Külotlu çorap","label_en": "Tights",   "swatch": "#3B6B8C", "href": "/products?cat=kulotlu-corap"},
            {"label_tr": "Sporcu çorabı","label_en": "Athletic", "swatch": "#9A9281", "href": "/products?cat=sporcu-corap"},
        ],
    },
    {
        "label_tr": "İç giyim", "label_en": "Innerwear", "order": 1,
        "feature_title": "Modal pamuk boxer",
        "feature_meta": "6'lı paket · 4 renk",
        "feature_image_url": "/home/hero-b.png",
        "children": [
            {"label_tr": "Erkek boxer",  "label_en": "Boxer briefs", "swatch": "#0E0E0C", "href": "/products?cat=erkek-boxer"},
            {"label_tr": "Erkek atlet",  "label_en": "Tank",         "swatch": "#FAF8F4", "href": "/products?cat=erkek-atlet"},
            {"label_tr": "Kadın külot",  "label_en": "Briefs",       "swatch": "#E9C7B8", "href": "/products?cat=kadin-kulot"},
            {"label_tr": "Kadın sütyen", "label_en": "Bras",         "swatch": "#B8654A", "href": "/products?cat=kadin-sutyen"},
            {"label_tr": "Termal seri",  "label_en": "Thermal",      "swatch": "#5C7C6F", "href": "/products?cat=termal"},
            {"label_tr": "Pijama",       "label_en": "Pajamas",      "swatch": "#3B6B8C", "href": "/products?cat=pijama"},
        ],
    },
    {
        "label_tr": "2026 Yaz", "label_en": "SS26", "order": 2,
        "feature_title": "SS26 · Yeni sezon",
        "feature_meta": "Vitrin · Mayıs 2026",
        "feature_image_url": "/home/season-ss26.png",
        "children": [
            {"label_tr": "Yeni gelenler",  "label_en": "New arrivals",  "swatch": "#B8654A", "href": "/products?season=ss26"},
            {"label_tr": "Pamuk serisi",   "label_en": "Cotton series", "swatch": "#FAF8F4", "href": "/products?season=ss26"},
            {"label_tr": "Bambu serisi",   "label_en": "Bamboo series", "swatch": "#5C7C6F", "href": "/products?season=ss26"},
            {"label_tr": "Spor & atletik", "label_en": "Athletic",      "swatch": "#0E0E0C", "href": "/products?season=ss26"},
        ],
    },
    {
        "label_tr": "2025 Kış", "label_en": "AW25", "order": 3,
        "feature_title": "Outlet · Kapanış indirimi",
        "feature_meta": "%30'a varan toptan",
        "feature_image_url": "/home/season-outlet.png",
        "children": [
            {"label_tr": "Termal çorap", "label_en": "Thermal socks", "swatch": "#3B6B8C", "href": "/products?season=aw25"},
            {"label_tr": "Yün karışım",  "label_en": "Wool blend",    "swatch": "#8C4A33", "href": "/products?season=aw25"},
            {"label_tr": "Ev çorabı",    "label_en": "Home socks",    "swatch": "#B0382F", "href": "/products?season=aw25"},
            {"label_tr": "Outlet · Kış", "label_en": "Outlet",        "swatch": "#6E685D", "href": "/products?season=aw25"},
        ],
    },
    {"label_tr": "Tüm sezonlar", "label_en": "All seasons", "order": 4, "href": "/products"},
    {
        "label_tr": "Markalar", "label_en": "Brands", "order": 5,
        "feature_title": "Lisanslı markalar",
        "feature_meta": "Resmi distribütör",
        "feature_image_url": "/home/season-all.png",
        "children": [
            {"label_tr": "Belino",          "label_en": "Belino",        "swatch": "#0E0E0C", "href": "/products?brand=Belino"},
            {"label_tr": "Pierre Cardin",   "label_en": "Pierre Cardin", "swatch": "#3B6B8C", "href": "/products"},
            {"label_tr": "U.S. Polo Assn.", "label_en": "U.S. Polo",     "swatch": "#B0382F", "href": "/products"},
            {"label_tr": "Lacoste",         "label_en": "Lacoste",       "swatch": "#5C7C6F", "href": "/products"},
        ],
    },
]

# Belino home page sections — minimal seed (asıl içerik halen
# React kodunda; ERP UI üzerinden zaman içinde DB'ye taşınır).
HOME_SECTIONS = [
    {
        "kind": "hero", "order": 0,
        "eyebrow_tr": "2026 İlkbahar/Yaz · Yeni sezon",
        "eyebrow_en": "SS26 · New season",
        "title_tr": "Toptanın yeni standardı.",
        "title_en": "The new standard of wholesale.",
        "body_tr": "Çorap ve iç giyimde 12.000+ varyant. Hızlı toptan sipariş, paket bazlı stok şeffaflığı.",
        "body_en": "12,000+ variants in socks and innerwear. Fast wholesale orders, pack-based stock transparency.",
        "image_url": "/home/hero-a.png",
        "cta_label_tr": "Koleksiyonu Keşfet", "cta_label_en": "Explore Collection",
        "cta_href": "/products",
    },
    {
        "kind": "trust", "order": 1,
        "title_tr": "Güven bandı", "title_en": "Trust strip",
    },
    {
        "kind": "seasons", "order": 2,
        "eyebrow_tr": "Kategoriler", "eyebrow_en": "Categories",
        "title_tr": "Sezona göre alışveriş", "title_en": "Shop by season",
    },
    {
        "kind": "featured", "order": 3,
        "eyebrow_tr": "Yeni gelenler", "eyebrow_en": "New arrivals",
        "title_tr": "Vitrin · Yeni Eklenenler", "title_en": "Showcase · Latest Additions",
    },
]

SEASON_CARDS = [
    {"key": "ss26",   "label_tr": "2026 İlkbahar/Yaz", "label_en": "SS26",        "eyebrow_tr": "SS26 · Yeni sezon",        "image_url": "/home/season-ss26.png",    "href": "/products?season=ss26",    "item_count": 248, "order": 0},
    {"key": "aw25",   "label_tr": "2025 Sonbahar/Kış", "label_en": "AW25",        "eyebrow_tr": "AW25 · Termal & yün",      "image_url": "/home/season-aw25.png",    "href": "/products?season=aw25",    "item_count": 186, "order": 1},
    {"key": "all",    "label_tr": "Tüm sezonlar",      "label_en": "All seasons", "eyebrow_tr": "Süreğen koleksiyon",       "image_url": "/home/season-all.png",     "href": "/products?season=all",     "item_count": 642, "order": 2},
    {"key": "outlet", "label_tr": "Outlet",            "label_en": "Outlet",      "eyebrow_tr": "%30'a varan toptan",       "image_url": "/home/season-outlet.png",  "href": "/products?season=outlet",  "item_count": 124, "order": 3},
]

TRUST_BADGES = [
    {"icon_key": "shield",  "title_tr": "Güvenli Alışveriş",     "title_en": "Secure Checkout",  "sub_tr": "SSL · 3D Secure",          "sub_en": "SSL · 3D Secure",       "order": 0},
    {"icon_key": "percent", "title_tr": "Toplu Alım İndirimi",   "title_en": "Bulk Discount",    "sub_tr": "Adete göre kademeli",      "sub_en": "Tiered by quantity",    "order": 1},
    {"icon_key": "truck",   "title_tr": "Ücretsiz Kargo",        "title_en": "Free Shipping",    "sub_tr": "5.000 TL üzeri",           "sub_en": "Over 5,000 TRY",        "order": 2},
    {"icon_key": "card",    "title_tr": "Taksit İmkanı",         "title_en": "Installments",     "sub_tr": "12 aya varan",             "sub_en": "Up to 12 months",       "order": 3},
    {"icon_key": "bolt",    "title_tr": "24 Saatte Kargo",       "title_en": "24h Shipping",     "sub_tr": "Aynı gün hazırlık",        "sub_en": "Same-day prep",         "order": 4},
]


def seed(apps, schema_editor):
    # Only seed Belino fixtures when migrating against the BELINO schema.
    # Other profiles (e.g. Demfirat on public) start empty so the operator
    # can fill nav/sections through the CMS UI.
    from django.conf import settings
    if (getattr(settings, "DB_SCHEMA", "public") or "public").upper() != "BELINO":
        return

    Storefront = apps.get_model("storefront", "Storefront")
    NavMenu = apps.get_model("storefront", "NavMenu")
    HomeSection = apps.get_model("storefront", "HomeSection")
    HomeSectionCard = apps.get_model("storefront", "HomeSectionCard")
    TrustBadge = apps.get_model("storefront", "TrustBadge")

    sf, created = Storefront.objects.get_or_create(
        key="belino",
        defaults={"name": "Belino B2B", "domain": "belino.com", "is_active": True},
    )
    if not created and sf.nav_items.exists():
        # Zaten seed edilmiş — tekrar ekleme.
        return

    # NAV
    for item in NAV_ITEMS:
        children = item.pop("children", [])
        parent = NavMenu.objects.create(storefront=sf, **item)
        for idx, c in enumerate(children):
            NavMenu.objects.create(storefront=sf, parent=parent, order=idx, **c)

    # HOME
    sec_objs = {}
    for sec in HOME_SECTIONS:
        obj = HomeSection.objects.create(storefront=sf, **sec)
        sec_objs[sec["kind"]] = obj

    for c in SEASON_CARDS:
        HomeSectionCard.objects.create(section=sec_objs["seasons"], **c)
    for b in TRUST_BADGES:
        TrustBadge.objects.create(section=sec_objs["trust"], **b)


def unseed(apps, schema_editor):
    Storefront = apps.get_model("storefront", "Storefront")
    Storefront.objects.filter(key="belino").delete()


class Migration(migrations.Migration):
    dependencies = [("storefront", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
