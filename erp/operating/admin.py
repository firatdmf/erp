from django.contrib import admin
from .models import *


# Order Admin with detailed fieldsets
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_variant', 'quantity', 'price', 'description']


class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'get_customer_name', 'is_guest_order', 'order_status', 'payment_status', 'paid_amount', 'created_at']
    list_filter = ['is_guest_order', 'order_status', 'payment_status', 'status', 'created_at']
    search_fields = ['order_number', 'guest_email', 'guest_first_name', 'guest_last_name', 'web_client__first_name', 'web_client__last_name']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'status', 'order_status', 'notes', 'created_at', 'updated_at')
        }),
        ('Customer Information', {
            'fields': ('web_client', 'is_guest_order', 'guest_first_name', 'guest_last_name', 'guest_email', 'guest_phone'),
            'description': 'For guest orders, web_client will be empty and guest fields will contain customer info.'
        }),
        ('Payment Information', {
            'fields': ('payment_id', 'payment_method', 'payment_status', 'card_type', 'card_association', 'card_last_four')
        }),
        ('Pricing', {
            'fields': ('original_currency', 'original_price', 'paid_currency', 'paid_amount', 'exchange_rate')
        }),
        ('Delivery Address', {
            'fields': ('delivery_address_title', 'delivery_address', 'delivery_city', 'delivery_country', 'delivery_phone')
        }),
        ('Billing Address', {
            'fields': ('billing_address_title', 'billing_address', 'billing_city', 'billing_country', 'billing_phone')
        }),
        ('Shipping & Tracking', {
            'fields': ('carrier', 'tracking_number', 'shipped_at', 'delivered_at')
        }),
        ('Invoice', {
            'fields': ('ettn', 'invoice_date'),
            'classes': ('collapse',)
        }),
    )
    
    def get_customer_name(self, obj):
        if obj.is_guest_order:
            return f"👤 {obj.guest_first_name or ''} {obj.guest_last_name or ''} (Misafir)"
        elif obj.web_client:
            return f"{obj.web_client.first_name} {obj.web_client.last_name}"
        return "-"
    get_customer_name.short_description = 'Customer'
    get_customer_name.admin_order_field = 'guest_first_name'


admin.site.register(Machine)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(MachineCredential)
admin.site.register(Warehouse)
admin.site.register(RawMaterialGood)
admin.site.register(RawMaterialGoodReceipt)
admin.site.register(RawMaterialGoodItem)