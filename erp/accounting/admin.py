from django.contrib import admin
from .models import (
    AssetCategory,
    EquityExpense,
    ExpenseCategory,
    CurrencyCategory,
    Income,
    IncomeCategory,
    CashAccount,
    EquityCapital,
    Book,
    # Source,
    Sale,
    Asset,
    # Equity,
    Stakeholder
)

admin.site.register(CurrencyCategory)
admin.site.register(Book)
# admin.site.register(Source)

admin.site.register(AssetCategory)
admin.site.register(ExpenseCategory)
admin.site.register(EquityExpense)
admin.site.register(IncomeCategory)
admin.site.register(Income)
admin.site.register(Sale)
admin.site.register(Asset)
# admin.site.register(Equity)
admin.site.register(Stakeholder)
admin.site.register(CashAccount)
admin.site.register(EquityCapital)


# Register your models here.
