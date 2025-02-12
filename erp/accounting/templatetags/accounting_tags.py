from collections import defaultdict
from django.db.models.functions import Coalesce
from django.db.models import Sum, F, DecimalField, Value
from django import template
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
import decimal
from accounting.models import EquityExpense, Book
from accounting.forms import *
import time

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
    starting_time = time.time()
    print("starting")
    print("expenses dollar")
    # Calculate total expenses for the current month


    print("now putting all in context")
    # Populate context with calculated data
    # context["expense_form"] = ExpenseForm(initial={"book":selected_book})
    # context["income_form"] = IncomeForm(initial={"book":selected_book})
    # context["book_selection_form"] = BookSelectionForm()
    context["csrf_token"] = csrf_token
    context["selected_book"] = selected_book
    ending_time = time.time()
    print(f"Total time it took: {ending_time-starting_time}")
    print("done")
    return render_to_string('accounting/components/book_component.html',context) 