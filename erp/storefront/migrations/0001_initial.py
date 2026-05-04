# Auto-written initial migration for storefront app.
# Generated manually because runserver --noreload bypasses makemigrations.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("marketing", "0001_initial"),  # ProductCategory + Product must exist
    ]

    operations = [
        migrations.CreateModel(
            name="Storefront",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=60, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("domain", models.CharField(blank=True, max_length=200)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Storefront", "verbose_name_plural": "Storefronts"},
        ),
        migrations.CreateModel(
            name="NavMenu",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label_tr", models.CharField(max_length=80)),
                ("label_en", models.CharField(max_length=80)),
                ("href", models.CharField(blank=True, max_length=300)),
                ("swatch", models.CharField(blank=True, max_length=20)),
                ("feature_title", models.CharField(blank=True, max_length=120)),
                ("feature_meta", models.CharField(blank=True, max_length=200)),
                ("feature_image_url", models.URLField(blank=True)),
                ("order", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="marketing.productcategory")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="storefront.navmenu")),
                ("storefront", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="nav_items", to="storefront.storefront")),
            ],
            options={"verbose_name": "Nav Item", "verbose_name_plural": "Nav (Header Menüsü)", "ordering": ("storefront", "parent_id", "order", "id")},
        ),
        migrations.CreateModel(
            name="HomeSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("hero", "Hero (büyük kapak)"), ("trust", "Güven Bandı (rozet sıra)"), ("seasons", "Sezonlar / Kategori Grid"), ("featured", "Vitrin (ürün listesi)")], max_length=20)),
                ("title_tr", models.CharField(blank=True, max_length=140)),
                ("title_en", models.CharField(blank=True, max_length=140)),
                ("eyebrow_tr", models.CharField(blank=True, max_length=80)),
                ("eyebrow_en", models.CharField(blank=True, max_length=80)),
                ("body_tr", models.TextField(blank=True)),
                ("body_en", models.TextField(blank=True)),
                ("image_url", models.URLField(blank=True)),
                ("cta_label_tr", models.CharField(blank=True, max_length=80)),
                ("cta_label_en", models.CharField(blank=True, max_length=80)),
                ("cta_href", models.CharField(blank=True, max_length=300)),
                ("order", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("storefront", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="home_sections", to="storefront.storefront")),
            ],
            options={"verbose_name": "Anasayfa Bölümü", "verbose_name_plural": "Anasayfa (Home)", "ordering": ("storefront", "order", "id")},
        ),
        migrations.CreateModel(
            name="HomeSectionCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(blank=True, max_length=60)),
                ("label_tr", models.CharField(max_length=120)),
                ("label_en", models.CharField(max_length=120)),
                ("eyebrow_tr", models.CharField(blank=True, max_length=120)),
                ("eyebrow_en", models.CharField(blank=True, max_length=120)),
                ("image_url", models.URLField(blank=True)),
                ("href", models.CharField(blank=True, max_length=300)),
                ("item_count", models.IntegerField(default=0)),
                ("order", models.IntegerField(default=0)),
                ("section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cards", to="storefront.homesection")),
            ],
            options={"verbose_name": "Kart", "verbose_name_plural": "Kartlar (Sezon/Kategori)", "ordering": ("section", "order", "id")},
        ),
        migrations.CreateModel(
            name="HomeSectionProduct",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.IntegerField(default=0)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="marketing.product")),
                ("section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="featured_products", to="storefront.homesection")),
            ],
            options={"verbose_name": "Vitrin Ürünü", "verbose_name_plural": "Vitrin Ürünleri", "ordering": ("section", "order", "id"), "unique_together": {("section", "product")}},
        ),
        migrations.CreateModel(
            name="TrustBadge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("icon_key", models.CharField(blank=True, max_length=40)),
                ("title_tr", models.CharField(max_length=80)),
                ("title_en", models.CharField(max_length=80)),
                ("sub_tr", models.CharField(blank=True, max_length=120)),
                ("sub_en", models.CharField(blank=True, max_length=120)),
                ("order", models.IntegerField(default=0)),
                ("section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="badges", to="storefront.homesection")),
            ],
            options={"verbose_name": "Güven Rozeti", "verbose_name_plural": "Güven Rozetleri", "ordering": ("section", "order", "id")},
        ),
    ]
