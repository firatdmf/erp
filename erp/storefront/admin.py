from django.contrib import admin
from .models import (
    Storefront, NavMenu, HomeSection, HomeSectionCard,
    HomeSectionProduct, TrustBadge,
)


class NavMenuInline(admin.TabularInline):
    model = NavMenu
    fk_name = "parent"
    extra = 0
    fields = ("label_tr", "label_en", "swatch", "href", "order", "is_active")


@admin.register(NavMenu)
class NavMenuAdmin(admin.ModelAdmin):
    list_display = ("label_tr", "parent", "storefront", "order", "is_active")
    list_filter = ("storefront", "is_active", "parent")
    search_fields = ("label_tr", "label_en")
    inlines = [NavMenuInline]


@admin.register(Storefront)
class StorefrontAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "domain", "is_active")
    search_fields = ("key", "name", "domain")


class HomeSectionCardInline(admin.TabularInline):
    model = HomeSectionCard
    extra = 0


class HomeSectionProductInline(admin.TabularInline):
    model = HomeSectionProduct
    extra = 0


class TrustBadgeInline(admin.TabularInline):
    model = TrustBadge
    extra = 0


@admin.register(HomeSection)
class HomeSectionAdmin(admin.ModelAdmin):
    list_display = ("kind", "title_tr", "storefront", "order", "is_active")
    list_filter = ("storefront", "kind", "is_active")
    inlines = [HomeSectionCardInline, HomeSectionProductInline, TrustBadgeInline]
