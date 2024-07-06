from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.views import View
from .models import Expense, ExpenseCategory
from .forms import ExpenseForm
from django.http import JsonResponse
from django.db.models import Q
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta


class index(TemplateView):
    template_name = "accounting/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=7)
        total_expenses = (
            Expense.objects.filter(date__gte=seven_days_ago).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        context["total_expenses"] = total_expenses
        return context


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
            return redirect("accounting/expense_list")
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
