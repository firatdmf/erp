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
    list_display = ('client', 'product_sku', 'variant_sku', 'quantity', 'is_custom_curtain', 'display_custom_price', 'created_at')
    list_filter = ('is_custom_curtain', 'created_at')
    search_fields = ('client__username', 'client__email', 'product_sku', 'variant_sku')
    readonly_fields = ('display_custom_attributes', 'created_at', 'updated_at')
    
    def display_custom_price(self, obj):
        if obj.is_custom_curtain and obj.custom_price:
            return f"${obj.custom_price}"
        return "-"
    display_custom_price.short_description = "Custom Price"
    
    def display_custom_attributes(self, obj):
        if obj.custom_attributes:
            import json
            return json.dumps(obj.custom_attributes, indent=2)
        return "No custom attributes"
    display_custom_attributes.short_description = "Custom Attributes"
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('client', 'product_sku', 'variant_sku', 'quantity')
        }),
        ('Custom Curtain', {
            'fields': ('is_custom_curtain', 'custom_price', 'display_custom_attributes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
