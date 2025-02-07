from django.contrib import admin
from .models import (
    AssetCategory,
    EquityRevenue,
    EquityExpense,
    ExpenseCategory,
    CurrencyCategory,
    Income,
    IncomeCategory,
    CashAccount,
    EquityCapital,
    Book,
    # Source,
    # Sale,
    Asset,
    # Equity,
    # Stakeholder,
    Invoice,
    InvoiceItem,
    Transaction,
    AccountBalance,
    StakeholderBook
)

from authentication.models import Member

admin.site.register(CurrencyCategory)
# admin.site.register(Source)

admin.site.register(AssetCategory)
admin.site.register(ExpenseCategory)
admin.site.register(EquityExpense)
admin.site.register(IncomeCategory)
admin.site.register(Income)
# admin.site.register(Sale)
admin.site.register(Asset)
# admin.site.register(Equity)
admin.site.register(CashAccount)
admin.site.register(EquityRevenue)
admin.site.register(EquityCapital)
admin.site.register(Transaction)
admin.site.register(AccountBalance)


# Register your models here.




# Below is for invoice
# -----------------------------------------------------------------------------------------------------
class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1  # One extra empty row for new items

class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceItemInline]
    list_display = ['invoice_number', 'company', 'due_date', 'total_amount']

admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(InvoiceItem)

# -----------------------------------------------------------------------------------------------------

# Below is for stakeholder book

class StakeholderBookInline(admin.TabularInline):
    model = StakeholderBook
    extra = 1

class StakeholderAdmin(admin.ModelAdmin):
    inlines = (StakeholderBookInline,)

class BookAdmin(admin.ModelAdmin):
    inlines = (StakeholderBookInline,)


# I register member in the authentication app, no need for this
# admin.site.register(Member, StakeholderAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(StakeholderBook)

# -----------------------------------------------------------------------------------------------------
