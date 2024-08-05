from django.shortcuts import render, redirect
from django.http import HttpResponse

# from django.views.generic import TemplateView
from django.views import View, generic
from .models import Expense, ExpenseCategory, Income, IncomeCategory

# from .models import Expense, ExpenseCategory, Income, IncomeCategory
from .forms import ExpenseForm, IncomeForm
from django.http import JsonResponse
from django.db.models import Q
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import decimal
from currency_converter import CurrencyConverter


class index(generic.TemplateView):
    template_name = "accounting/index.html"

    def get_context_data(self, **kwargs):
        # Returns a dictionary representing the template context.
        context = super().get_context_data(**kwargs)
        # July 15, 2024
        today = timezone.localtime(timezone.now()).date()
        # print(timezone.localtime(timezone.now()))
        # 15
        # July 1, 2024
        beginning_of_month = today - timedelta(days=(today.day - 1))
        total_expense = (
            Expense.objects.filter(
                date__gte=beginning_of_month, date__lte=today, currency=1
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # Accounting for Euro
        total_expense += decimal.Decimal(
            "%.2f"
            % CurrencyConverter().convert(
                Expense.objects.filter(
                    date__gte=beginning_of_month, date__lte=today, currency=2
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
                    date__gte=beginning_of_month, date__lte=today, currency=3
                ).aggregate(total=Sum("amount"))["total"]
                or 0,
                "TRY",
                "USD",
            )
        )

        # Total income for USD
        total_income = (
            Income.objects.filter(
                date__gte=beginning_of_month, date__lte=today,currency=1
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        # Accounting for Euro
        total_income += decimal.Decimal(
            "%.2f"
            % CurrencyConverter().convert(
                Income.objects.filter(
                    date__gte=beginning_of_month, date__lte=today, currency=2
                ).aggregate(total=Sum("amount"))["total"]
                or 0,
                "EUR",
                "USD",
            )
        )
        # income accounting for TRY
        total_income += decimal.Decimal(
            "%.2f"
            % CurrencyConverter().convert(
                Income.objects.filter(
                    date__gte=beginning_of_month, date__lte=today, currency=3
                ).aggregate(total=Sum("amount"))["total"]
                or 0,
                "TRY",
                "USD",
            )
        )

        # total_income = (Income.objects.filter)
        context["total_expense"] = total_expense
        context["total_income"] = total_income
        # Currency 1 stands for dollar
        context["expense_form"] = ExpenseForm()
        context["income_form"] = IncomeForm()
        context["total_net"] = total_income - total_expense
        return context

    def post(self, request, *args, **kwargs):
        currencies = ["USD", "EUR", "TRY"]
        expense_form = ExpenseForm(request.POST)
        income_form = IncomeForm(request.POST)
        context = self.get_context_data()
        if expense_form.is_valid() and request.POST["expenseOrIncome"] == "expense":
            money_amount = request.POST.get("amount")
            money_currency = request.POST.get("currency")
            expense_form.save()
            # return redirect("/accounting/")
            response = HttpResponse()
            if money_currency != 1:
                money_amount = decimal.Decimal(
                    "%.2f"
                    % CurrencyConverter().convert(
                        money_amount, currencies[int(money_currency) - 1], "USD"
                    )
                )
                context["total_expense"] += money_amount
            response.write(
                # f'<p>Total Income this month: ${context["total_income"]}</p><p>Total expenses occured this month is: ${context["total_expense"]+money_amount}</p><p>Net: ${context["total_income"]-(context["total_expense"]+money_amount)}</p>'
                f'<p>Total Income this month: ${context["total_income"]}</p><p>Total expenses occured this month is: ${context["total_expense"]}</p><p>Net: ${context["total_income"]-context["total_expense"]}</p>'
            )
            return response
        if income_form.is_valid() and request.POST["expenseOrIncome"] == "income":
            money_amount = request.POST.get("amount")
            money_currency = request.POST.get("currency")
            income_form.save()
            response = HttpResponse()
            if money_currency != 1:
                money_amount = decimal.Decimal(
                    "%.2f"
                    % CurrencyConverter().convert(
                        money_amount, currencies[int(money_currency) - 1], "USD"
                    )
                )
                context["total_income"] += money_amount
            response.write(
                f'<p>Total Income this month: ${context["total_income"]}</p><p>Total expenses occured this month is: ${context["total_expense"]}</p><p>Net: ${context["total_income"]-context["total_expense"]}</p>'
            )
            return response

        # Currency 1 stands for dollar
        context = self.get_context_data()
        context["expense_form"] = ExpenseForm()
        context["income_form"] = IncomeForm()
        return self.render_to_response(context)


# class ExpenseView(View):
#     def get(self, request):
#         form = ExpenseForm()
#         return render(request, "accounting/expense_form.html", {"form": form})

#     def post(self, request):
#         form = ExpenseForm(request.POST)
#         if form.is_valid():
#             category_name = form.cleaned_data["category_name"]
#             if (category_name) != "":
#                 category, created = ExpenseCategory.objects.get_or_create(
#                     name=category_name
#                 )
#             expense = Expense(
#                 category=category,
#                 amount=form.cleaned_data["amount"],
#                 date=form.cleaned_data["date"],
#             )
#             expense.save()
#             return redirect("/accounting")
#         return render(request, "accounting/expense_form.html", {"form": form})


class CategorySearchView(View):
    def get(self, request):
        query = request.GET.get("query", "")
        if query:
            categories = ExpenseCategory.objects.filter(name__icontains=query)
        else:
            categories = ExpenseCategory.objects.none()
        data = [{"id": category.id, "name": category.name} for category in categories]
        return JsonResponse(data, safe=False)
