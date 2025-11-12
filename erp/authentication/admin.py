from django.contrib import admin

from accounting.admin import StakeholderBookInline
from .models import Member, Permission, WebClient, ClientAddress, Favorite, CartItem
# Register your models here.

# admin.site.register(Member)

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user',)
    filter_horizontal = ('permissions',)
    inlines = (StakeholderBookInline,)


@admin.register(WebClient)
class WebClientAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('username', 'email', 'name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Account Info', {
            'fields': ('username', 'email', 'name', 'password')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ClientAddress)
class ClientAddressAdmin(admin.ModelAdmin):
    list_display = ('client', 'title', 'city', 'country', 'is_default', 'created_at')
    list_filter = ('is_default', 'created_at', 'country')
    search_fields = ('client__username', 'client__email', 'title', 'city')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('client', 'product_sku', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('client__username', 'client__email', 'product_sku')
    readonly_fields = ('created_at',)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('client', 'product_sku', 'variant_sku', 'quantity', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('client__username', 'client__email', 'product_sku', 'variant_sku')
    readonly_fields = ('created_at', 'updated_at')
