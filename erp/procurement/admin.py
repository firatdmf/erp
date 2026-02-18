from django.contrib import admin
from .models import PurchaseRequest, PurchaseRequestItem, RequestForQuotation, PurchaseOrder, PurchaseOrderItem

class PurchaseRequestItemInline(admin.TabularInline):
    model = PurchaseRequestItem
    extra = 1

@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'requester', 'department', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'department')
    search_fields = ('requester__username', 'reason')
    inlines = [PurchaseRequestItemInline]

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'status', 'total_amount', 'order_date')
    list_filter = ('status', 'order_date')
    search_fields = ('supplier__company_name', 'supplier__contact_name')
    inlines = [PurchaseOrderItemInline]

@admin.register(RequestForQuotation)
class RFQAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'status', 'deadline')
    list_filter = ('status',)
