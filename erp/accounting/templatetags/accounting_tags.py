from collections import defaultdict
from django.db.models.functions import Coalesce
from django.db.models import Sum, F, DecimalField, Value
from django import template
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
import decimal
from currency_converter import CurrencyConverter
from accounting.models import Expense, Income, Book
from accounting.forms import ExpenseForm, IncomeForm

register = template.Library()

@register.simple_tag
def sales_report():
    return render_to_string('accounting/components/sales_component.html',{"context":"hello moto"})

@register.simple_tag
def book_component(csrf_token,selected_book):
    print('----')
    print(selected_book)
    print('----')
    context = {}
    today = timezone.localtime(timezone.now()).date()
    beginning_of_month = today - timedelta(days=(today.day - 1))


    # Calculate total expenses for the current month
    total_expense = (
        Expense.objects.filter(
            date__gte=beginning_of_month, date__lte=today, currency=1,book=selected_book
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    
    # Accounting for Euro
    total_expense += decimal.Decimal(
        "%.2f"
        % CurrencyConverter().convert(
            Expense.objects.filter(
                date__gte=beginning_of_month, date__lte=today, currency=2,book=selected_book
            ).aggregate(total=Sum("amount"))["total"]
            or 0,
            "EUR",
            "USD",
        )
    )
    
    # Accounting for TRY
    total_expense += decimal.Decimal(
        "%.2f"
        % CurrencyConverter().convert(
            Expense.objects.filter(
                date__gte=beginning_of_month, date__lte=today, currency=3,book=selected_book
            ).aggregate(total=Sum("amount"))["total"]
            or 0,
            "TRY",
            "USD",
        )
    )

    # Calculate total income for the current month
    total_income = (
        Income.objects.filter(
            date__gte=beginning_of_month, date__lte=today, currency=1,book=selected_book
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    
    # Accounting for Euro
    total_income += decimal.Decimal(
        "%.2f"
        % CurrencyConverter().convert(
            Income.objects.filter(
                date__gte=beginning_of_month, date__lte=today, currency=2,book=selected_book
            ).aggregate(total=Sum("amount"))["total"]
            or 0,
            "EUR",
            "USD",
        )
    )
    
    # Accounting for TRY
    total_income += decimal.Decimal(
        "%.2f"
        % CurrencyConverter().convert(
            Income.objects.filter(
                date__gte=beginning_of_month, date__lte=today, currency=3,book=selected_book
            ).aggregate(total=Sum("amount"))["total"]
            or 0,
            "TRY",
            "USD",
        )
    )

    # Populate context with calculated data
    context["total_expense"] = total_expense
    context["total_income"] = total_income
    context["expense_form"] = ExpenseForm(initial={"book":selected_book})
    context["income_form"] = IncomeForm(initial={"book":selected_book})
    # context["book_selection_form"] = BookSelectionForm()
    context["total_net"] = total_income - total_expense
    context["csrf_token"] = csrf_token
    context["selected_book"] = selected_book
    return render_to_string('accounting/components/book_component.html',context)