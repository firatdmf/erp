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
    return render_to_string(
        "accounting/components/sales_component.html", {"context": "hello moto"}
    )


@register.simple_tag
def book_component(csrf_token, selected_book):
    print("----")
    print(selected_book)
    print("----")
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
    return render_to_string("accounting/components/book_component.html", context)


@register.filter
# makes 10000 to 10,000.00
def format_money(value):
    if not isinstance(value, (int, float, Decimal)):
        return value
    return f"{value:,.2f}"


@register.simple_tag
def exchange_rates_component():
    from accounting.services import get_exchange_rate

    base_currency = get_base_currency()
    rates = []

    for currency in CurrencyCategory.objects.all():
        if currency == base_currency:
            continue
        rate = get_exchange_rate(currency.code, base_currency.code)
        if rate is not None:
            rates.append({
                "from_currency": currency,
                "rate": rate,
            })

    context = {
        "base_currency": base_currency,
        "rates": rates,
    }
    return render_to_string(
        "accounting/components/exchange_rates_component.html", context
    )


@register.simple_tag
def net_worth_component(book_pk):
    from accounting.views import get_total_base_currency_balance
    from accounting.services import get_exchange_rate

    book = Book.objects.get(pk=book_pk)
    base_currency = get_base_currency()

    # Cash total (already in base currency)
    cash_total = get_total_base_currency_balance(book_pk=book_pk)

    # Fixed assets total converted to base currency
    fixed_assets = AssetFixedAsset.objects.filter(book=book)
    assets_list = []
    assets_total = Decimal("0.00")

    for asset in fixed_assets:
        if asset.currency == base_currency:
            value_base = asset.value
        else:
            rate = get_exchange_rate(asset.currency.code, base_currency.code)
            value_base = (asset.value * rate).quantize(Decimal("0.01")) if rate else asset.value

        assets_total += value_base
        assets_list.append({
            "asset": asset,
            "value_base": value_base,
        })

    net_worth = cash_total + assets_total

    context = {
        "base_currency": base_currency,
        "cash_total": cash_total,
        "assets_total": assets_total,
        "net_worth": net_worth,
        "assets_list": assets_list,
        "book_pk": book_pk,
    }
    return render_to_string(
        "accounting/components/net_worth_component.html", context
    )


@register.simple_tag
def kpi_dashboard_component(book_pk):
    from accounting.views import get_total_base_currency_balance

    book = Book.objects.get(pk=book_pk)
    today = timezone.now().date()
    start_of_month = today.replace(day=1)

    # For base currency totals
    base_currency = get_base_currency()
    total_balance = get_total_base_currency_balance(book_pk=book_pk)
    base_avg_burn = 5000  # usd
    base_runway = Decimal(total_balance / base_avg_burn)

    # Dictionary per currency
    currency_kpis = []

    for currency in CurrencyCategory.objects.all():
        # Balance
        balance = CashAccount.objects.filter(book=book, currency=currency).aggregate(
            total_balance=Sum("balance")
        )["total_balance"] or Decimal("0.00")

        # Transactions this month in this currency
        transactions = CashTransactionEntry.objects.filter(
            book=book,
            currency=currency,
            created_at__date__gte=start_of_month,
            created_at__date__lte=today,
        )

        money_in = sum(t.amount for t in transactions if t.is_amount_positive)
        money_out = sum(t.amount for t in transactions if not t.is_amount_positive)

        burn = money_out - money_in
        avg_burn = Decimal("5000.00")  # can later be dynamic per currency
        runway = (balance / avg_burn).quantize(Decimal("0.1")) if avg_burn > 0 else None

        growth_rate = (
            ((balance + money_in) / balance * 100 - 100).quantize(Decimal("0.1"))
            if balance > 0
            else None
        )

        default_alive = balance > 0

        currency_kpis.append(
            {
                "currency": currency,
                "balance": balance,
                "money_in": money_in,
                "money_out": money_out,
                "burn": burn,
                "runway": runway,
                "growth_rate": growth_rate,
                "default_alive": default_alive,
            }
        )

    context = {
        "base_currency": base_currency,
        "total_balance": total_balance,
        "base_runway":base_runway,
        "currency_kpis": currency_kpis,
    }

    return render_to_string(
        "accounting/components/kpi_dashboard_component.html", context
    )
