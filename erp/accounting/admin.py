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

admin.site.register(AssetAccountsReceivable)
admin.site.register(LiabilityAccountsPayable)
# admin.site.register(Invoice)
admin.site.register(AssetInventoryRawMaterial)
# admin.site.register(RawMaterialGoodsReceipt)
admin.site.register(AssetInventoryFinishedGood)

admin.site.register(CurrencyExchange)