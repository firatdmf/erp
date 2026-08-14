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


class StockMovementAdmin(admin.ModelAdmin):
    """Raw view of the stock ledger — every metre in or out, with what
    caused it. The app's own screens (product detail → Stock movements)
    show the same rows formatted; this is for searching across them."""
    list_display = ["created_at", "movement_type", "quantity", "product",
                    "roll", "order", "reason", "created_by"]
    list_filter = ["movement_type", "created_at", "product__warehouse"]
    search_fields = ["reason", "reference", "roll__barcode",
                     "product__name", "product__sku"]
    # FK dropdowns over thousands of rolls/products would render as huge
    # selects and time the page out; raw ids keep it usable.
    raw_id_fields = ["product", "roll", "order", "reservation", "created_by"]
    date_hierarchy = "created_at"
    # The ledger is a record of what happened — editable here only because
    # a wrong row occasionally needs correcting by hand; nothing recomputes
    # from an edit, so quantities changed here will NOT move stock.
    readonly_fields = ["created_at"]


class OrderRollReservationAdmin(admin.ModelAdmin):
    """Which rolls are spoken for by which orders. `consumed=False` is a
    live hold (nothing deducted yet); True means it shipped and became a
    StockMovement(out)."""
    list_display = ["created_at", "order", "roll", "meters",
                    "warehouse_product", "consumed", "consumed_at", "created_by"]
    list_filter = ["consumed", "created_at"]
    search_fields = ["roll__barcode", "order__order_number",
                     "warehouse_product__name", "warehouse_product__sku"]
    raw_id_fields = ["order", "order_item", "roll", "warehouse_product", "created_by"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at"]


admin.site.register(Machine)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(MachineCredential)
admin.site.register(Warehouse)
admin.site.register(RawMaterialGood)
admin.site.register(RawMaterialGoodReceipt)
admin.site.register(RawMaterialGoodItem)
admin.site.register(StockMovement, StockMovementAdmin)
admin.site.register(OrderRollReservation, OrderRollReservationAdmin)