from django.contrib import admin
from .models import (
    Expense,
    ExpenseCategory,
    CurrencyCategory,
    Income,
    IncomeCategory,
    Book,
    Account,
    Sale,
    Asset,
    Capital,
    CashCategory,
    Stakeholder
)

admin.site.register(CurrencyCategory)
admin.site.register(Book)
admin.site.register(Account)
admin.site.register(ExpenseCategory)
admin.site.register(Expense)
admin.site.register(IncomeCategory)
admin.site.register(Income)
admin.site.register(Sale)
admin.site.register(Asset)
admin.site.register(Capital)
admin.site.register(CashCategory)
admin.site.register(Stakeholder)


# Register your models here.
