from django.contrib import admin
from .models import *

from authentication.models import Member

admin.site.register(CurrencyCategory)
# admin.site.register(Source)

admin.site.register(ExpenseCategory)
admin.site.register(EquityExpense)
# admin.site.register(Sale)
# admin.site.register(Equity)
# admin.site.register(CashAccount)
admin.site.register(EquityRevenue)
admin.site.register(EquityCapital)
admin.site.register(EquityDivident)
admin.site.register(CashTransactionEntry)


# Register your models here.




# Below is for invoice
# -----------------------------------------------------------------------------------------------------
# class InvoiceItemInline(admin.TabularInline):
#     model = InvoiceItem
#     extra = 1  # One extra empty row for new items

# class InvoiceAdmin(admin.ModelAdmin):
#     inlines = [InvoiceItemInline]
#     list_display = ['invoice_number', 'company', 'due_date', 'total_amount']

# admin.site.register(Invoice, InvoiceAdmin)
# admin.site.register(InvoiceItem)

# -----------------------------------------------------------------------------------------------------

# Below is for stakeholder book

class StakeholderBookInline(admin.TabularInline):
    model = StakeholderBook
    extra = 1

# class StakeholderBookAdmin(admin.ModelAdmin):
#     inlines = (StakeholderBookInline,)

class BookAdmin(admin.ModelAdmin):
    inlines = (StakeholderBookInline,)


# I register member in the authentication app, no need for this
# admin.site.register(Member, StakeholderAdmin)
admin.site.register(Book, BookAdmin)
# admin.site.register(StakeholderBook)
# -----------------------------------------------------------------------------------------------------
admin.site.register(AssetCash)

@admin.register(CashAccount)
class CashAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'book', 'currency', 'balance')
    search_fields = ('name', 'book__name')


# @admin.register(AssetCash)
# class AssetCashAdmin(admin.ModelAdmin):
#     list_display = ('book','currency','amount','currency_balance')
#     search_fields =  ('currency__name','currency__code','currency__symbol','book__name')

# admin.site.register(Invoice)
admin.site.register(AssetInventoryRawMaterial)
# admin.site.register(RawMaterialGoodsReceipt)
admin.site.register(AssetInventoryFinishedGood)

admin.site.register(CurrencyExchange)

# ---------------------------------------------------------------------------
# Current-account (cari) ledger admin — merged in from the former
# current_account app. Models arrive via the `from .models import *` above.
# ---------------------------------------------------------------------------
@admin.register(CariAccount)
class CariAccountAdmin(admin.ModelAdmin):
    list_display  = ("code", "name", "type", "book", "default_currency",
                     "cached_balance", "credit_limit", "is_active")
    list_filter   = ("type", "is_active", "book")
    search_fields = ("code", "name", "tax_number", "identity_number", "email", "phone")
    raw_id_fields = ("contact", "company", "supplier")
    readonly_fields = ("cached_balance", "last_movement_at",
                       "created_at", "updated_at")


@admin.register(CariMovement)
class CariMovementAdmin(admin.ModelAdmin):
    list_display  = ("date", "cari", "movement_type", "amount", "currency",
                     "amount_base", "reference")
    list_filter   = ("movement_type", "currency", "book")
    search_fields = ("cari__code", "cari__name", "description", "reference")
    raw_id_fields = ("cari",)
    readonly_fields = ("amount_base", "exchange_rate", "created_at")


@admin.register(CariSettings)
class CariSettingsAdmin(admin.ModelAdmin):
    list_display = ("book", "cari_code_prefix", "next_cari_seq",
                    "default_tax_rate", "default_payment_term_days")


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ("subtotal", "discount_amount", "tax_amount", "total")
    fields = ("line_no", "description", "quantity", "unit", "unit_price",
              "discount_rate", "tax_rate", "subtotal", "tax_amount", "total")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "series", "type", "status", "cari", "date",
                    "due_date", "total", "balance", "currency")
    list_filter = ("type", "status", "book", "currency")
    search_fields = ("number", "cari__name", "cari__code", "notes")
    raw_id_fields = ("cari", "book", "order", "posted_movement")
    readonly_fields = ("subtotal", "discount_amount", "tax_amount", "total",
                       "balance", "paid_amount", "created_at", "updated_at")
    inlines = [InvoiceItemInline]


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0
    raw_id_fields = ("invoice",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("number", "type", "method", "status", "cari", "date",
                    "amount", "currency", "cash_account")
    list_filter = ("type", "method", "status", "book", "currency")
    search_fields = ("number", "cari__name", "cari__code", "description")
    raw_id_fields = ("cari", "book", "cash_account", "posted_movement")
    readonly_fields = ("posted_movement", "created_at", "updated_at")
    inlines = [PaymentAllocationInline]


@admin.register(CheckOrPromissoryNote)
class CheckAdmin(admin.ModelAdmin):
    list_display = ("serial_no", "instrument", "direction", "status",
                    "cari", "amount", "currency", "due_date")
    list_filter = ("instrument", "direction", "status", "book")
    search_fields = ("serial_no", "bank", "drawer", "cari__name", "cari__code")
    raw_id_fields = ("cari", "book", "endorsed_to", "posted_movement",
                     "endorse_movement", "cleared_cash_account")
    readonly_fields = ("posted_movement", "endorse_movement", "cleared_cash_account",
                       "created_at", "updated_at")
