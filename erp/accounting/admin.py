from django.contrib import admin
from .models import Expense,ExpenseCategory, CurrencyCategory, Income, IncomeCategory, Book
admin.site.register(Expense)
admin.site.register(ExpenseCategory)
admin.site.register(CurrencyCategory)
admin.site.register(Income)
admin.site.register(IncomeCategory)
admin.site.register(Book)

# Register your models here.
