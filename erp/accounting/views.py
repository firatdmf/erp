from django.shortcuts import render, redirect
from django.http import HttpResponse

# from django.views.generic import TemplateView
from django.views import View, generic
from .models import Expense, ExpenseCategory, Income, IncomeCategory
from .forms import ExpenseForm
from django.http import JsonResponse
from django.db.models import Q
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta


class index(generic.TemplateView):
    template_name = "accounting/index.html"

    def get_context_data(self, **kwargs):
        # Returns a dictionary representing the template context.
        context = super().get_context_data(**kwargs)
        # July 15, 2024
        today = timezone.now().date()
        # 15
        # July 1, 2024
        beginning_of_month = today - timedelta(days=(today.day-1))
        total_expense = (
            Expense.objects.filter(date__gte=beginning_of_month,date__lte=today).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        total_income = (
            Income.objects.filter(date__gte=beginning_of_month).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        # total_income = (Income.objects.filter)
        context["total_expense"] = total_expense
        context ["expense_form"] = ExpenseForm()
        return context
    
    def post(self, request, *args, **kwargs):
        expense_form = ExpenseForm(request.POST)
        
        if expense_form.is_valid():
            money_amount = request.POST.get("amount")
            expense_form.save()
            # return redirect("/accounting/")
            response = HttpResponse()
            response.write(f'{money_amount} has been saved as an expense')
            return response
        context = self.get_context_data()
        context ["expense_form"] = ExpenseForm()
        return self.render_to_response(context)


class ExpenseView(View):
    def get(self, request):
        form = ExpenseForm()
        return render(request, "accounting/expense_form.html", {"form": form})

    def post(self, request):
        form = ExpenseForm(request.POST)
        if form.is_valid():
            category_name = form.cleaned_data["category_name"]
            category, created = ExpenseCategory.objects.get_or_create(
                name=category_name
            )
            expense = Expense(
                category=category,
                amount=form.cleaned_data["amount"],
                date=form.cleaned_data["date"],
            )
            expense.save()
            return redirect("/accounting")
        return render(request, "accounting/expense_form.html", {"form": form})


class CategorySearchView(View):
    def get(self, request):
        query = request.GET.get("query", "")
        if query:
            categories = ExpenseCategory.objects.filter(name__icontains=query)
        else:
            categories = ExpenseCategory.objects.none()
        data = [{"id": category.id, "name": category.name} for category in categories]
        return JsonResponse(data, safe=False)
