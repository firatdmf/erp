"""
Storefront — Shopify-tarzı online mağaza CMS'i.

Header menüsü, anasayfa bölümleri, vitrin ürünleri vb. içeriği DB'den
yönetilir; Belino (Next.js) bu app'in API endpoint'lerinden çekip
kendi UI'ını besler. Bu sayede ERP'den içerik düzenlenebilir, yeniden
deploy gerekmez.

Şu an bir tenant = bir Storefront varsayıyoruz (BELINO schema → belino
storefront, public → demfirat). İleride çoklu storefront destekleyebiliriz.
"""
from django.db import models
from marketing.models import Product, ProductCategory


class Storefront(models.Model):
    """Bir tenant'ın online mağazası."""
    key = models.SlugField(max_length=60, unique=True, help_text="URL/API key — örn. 'belino'")
    name = models.CharField(max_length=120, help_text="Görünür ad — örn. 'Belino B2B'")
    domain = models.CharField(max_length=200, blank=True, help_text="örn. belino.com")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Storefront"
        verbose_name_plural = "Storefronts"

    def __str__(self):
        return self.name


class NavMenu(models.Model):
    """
    Header'da görünen tek bir nav öğesi. parent boşsa top-level (Çorap,
    İç giyim, ...). parent varsa sub-item (flyout içindeki link).

    feature_* alanları yalnızca top-level item'larda anlamlı: flyout'un
    sağındaki büyük "vitrin" kartının görseli ve metni.
    """
    storefront = models.ForeignKey(
        Storefront, on_delete=models.CASCADE, related_name="nav_items"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children",
    )

    # Görüntü
    label_tr = models.CharField(max_length=80)
    label_en = models.CharField(max_length=80)

    # Hedef — ya direkt URL ya da bir kategoriye bağlı
    href = models.CharField(
        max_length=300, blank=True,
        help_text="Boş bırakılırsa kategori veya children'a göre çözülür",
    )
    category = models.ForeignKey(
        ProductCategory, on_delete=models.SET_NULL, null=True, blank=True,
    )

    # Sub-item swatch (Belino sub-item swatch ihtiyacı için)
    swatch = models.CharField(
        max_length=20, blank=True,
        help_text="Hex renk — alt menü swatch'i için (örn. #0E0E0C)",
    )

    # Top-level flyout vitrin kartı
    feature_title = models.CharField(max_length=120, blank=True)
    feature_meta = models.CharField(max_length=200, blank=True)
    feature_image_url = models.URLField(blank=True, help_text="/home/... veya tam URL")

    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("storefront", "parent_id", "order", "id")
        verbose_name = "Nav Item"
        verbose_name_plural = "Nav (Header Menüsü)"

    def __str__(self):
        prefix = "└ " if self.parent_id else ""
        return f"{prefix}{self.label_tr}"


class HomeSection(models.Model):
    """
    Anasayfanın bir bölümü. kind, hangi React bileşenini render edeceğimizi
    belirler. Tüm bölümler tek bir tabloda — anasayfa bölümlerini drag-drop
    ile yeniden sıralamak için tek `order` field yeterli.
    """
    KIND_HERO = "hero"
    KIND_TRUST = "trust"
    KIND_SEASONS = "seasons"
    KIND_FEATURED = "featured"
    KIND_CHOICES = [
        (KIND_HERO, "Hero (büyük kapak)"),
        (KIND_TRUST, "Güven Bandı (rozet sıra)"),
        (KIND_SEASONS, "Sezonlar / Kategori Grid"),
        (KIND_FEATURED, "Vitrin (ürün listesi)"),
    ]

    storefront = models.ForeignKey(
        Storefront, on_delete=models.CASCADE, related_name="home_sections"
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)

    title_tr = models.CharField(max_length=140, blank=True)
    title_en = models.CharField(max_length=140, blank=True)
    eyebrow_tr = models.CharField(max_length=80, blank=True)
    eyebrow_en = models.CharField(max_length=80, blank=True)
    body_tr = models.TextField(blank=True)
    body_en = models.TextField(blank=True)

    image_url = models.URLField(blank=True, help_text="Hero/seasons kapak görseli")
    cta_label_tr = models.CharField(max_length=80, blank=True)
    cta_label_en = models.CharField(max_length=80, blank=True)
    cta_href = models.CharField(max_length=300, blank=True)

    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("storefront", "order", "id")
        verbose_name = "Anasayfa Bölümü"
        verbose_name_plural = "Anasayfa (Home)"

    def __str__(self):
        return f"{self.get_kind_display()} · {self.title_tr or self.eyebrow_tr or '—'}"


class HomeSectionCard(models.Model):
    """
    HomeSection.KIND_SEASONS gibi bölümlerin içindeki kart listesi.
    (Sezonlar bölümü için: SS26 / AW25 / All / Outlet — her biri bir
    HomeSectionCard.)
    """
    section = models.ForeignKey(
        HomeSection, on_delete=models.CASCADE, related_name="cards"
    )
    key = models.SlugField(max_length=60, blank=True, help_text="örn. ss26")
    label_tr = models.CharField(max_length=120)
    label_en = models.CharField(max_length=120)
    eyebrow_tr = models.CharField(max_length=120, blank=True)
    eyebrow_en = models.CharField(max_length=120, blank=True)
    image_url = models.URLField(blank=True)
    href = models.CharField(max_length=300, blank=True)
    item_count = models.IntegerField(default=0, help_text="Görsel rozet (örn. '248 ürün')")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ("section", "order", "id")
        verbose_name = "Kart"
        verbose_name_plural = "Kartlar (Sezon/Kategori)"

    def __str__(self):
        return f"{self.label_tr} ({self.section.kind})"


class HomeSectionProduct(models.Model):
    """HomeSection.KIND_FEATURED için ürün listesi."""
    section = models.ForeignKey(
        HomeSection, on_delete=models.CASCADE, related_name="featured_products"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ("section", "order", "id")
        unique_together = (("section", "product"),)
        verbose_name = "Vitrin Ürünü"
        verbose_name_plural = "Vitrin Ürünleri"

    def __str__(self):
        return f"{self.product} @ {self.section}"


class TrustBadge(models.Model):
    """
    Güven bandı rozetleri (Güvenli Alışveriş, 24sa Kargo, vs).
    HomeSection.KIND_TRUST'a bağlı; ayrı tablo olarak tutuyoruz çünkü
    bunların kendine özgü ikon + alt etiket alanı var.
    """
    section = models.ForeignKey(
        HomeSection, on_delete=models.CASCADE, related_name="badges"
    )
    icon_key = models.CharField(
        max_length=40, blank=True,
        help_text="shield, percent, truck, card, bolt vs (Belino tarafında SVG mapping)",
    )
    title_tr = models.CharField(max_length=80)
    title_en = models.CharField(max_length=80)
    sub_tr = models.CharField(max_length=120, blank=True)
    sub_en = models.CharField(max_length=120, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ("section", "order", "id")
        verbose_name = "Güven Rozeti"
        verbose_name_plural = "Güven Rozetleri"

    def __str__(self):
        return self.title_tr
