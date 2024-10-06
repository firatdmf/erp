from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse

# from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.views import View, generic
from .models import Expense, ExpenseCategory, Income, IncomeCategory, Book, Asset, Equity, Stakeholder,CashAccount, EquityCapital

# from .models import Expense, ExpenseCategory, Income, IncomeCategory
from .forms import ExpenseForm, IncomeForm, AssetForm,StakeholderForm, BookForm, EquityCapitalForm
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
        context = super().get_context_data(**kwargs)
        books = Book.objects.all()
        context["books"] = books
        print(books)
        return context
    

class CreateBook(generic.edit.CreateView):
    model = Book
    form_class = BookForm
    template_name = "accounting/create_book.html"
    # Takes you to the newly created book's detail page
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.object.pk})


class BookDetail(generic.DetailView):
    model = Book
    template_name = "accounting/book_detail.html"
    context_object_name = "Book"

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        # book = Book.objects.get(pk=self.kwargs.get('pk'))
        book = self.get_object()
        # print(type(book))
        context['Stakeholders'] = Stakeholder.objects.filter(books=book)
        print(type(Stakeholder.objects.filter(books=book)))
        # print(context['Stakeholders'])
        return context


class CategorySearchView(View):
    def get(self, request):
        query = request.GET.get("query", "")
        if query:
            categories = ExpenseCategory.objects.filter(name__icontains=query)
        else:
            categories = ExpenseCategory.objects.none()
        data = [{"id": category.id, "name": category.name} for category in categories]
        return JsonResponse(data, safe=False)


class SalesView(generic.TemplateView):
    template_name = "accounting/sales_report.html"


class CreateAsset(generic.edit.CreateView):
    model = Asset
    form_class = AssetForm
    template_name = "accounting/create_asset.html"
    # success_url = "accounting/books/"

    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {'book': book}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass the book to the template if needed
        context['book'] = Book.objects.get(pk=self.kwargs.get('pk'))
        return context
    
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})


class AddEquityCapital(generic.edit.CreateView):
    model = EquityCapital
    form_class = EquityCapitalForm
    template_name = "accounting/add_equity_capital.html"
    # fields = "__all__"

    
    # This sends to the form data on what book is this thing
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        print(book)
        kwargs['book'] = book
        return kwargs
    
    # below preselected the book field of the capital model
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {'book': book}
    
    # You do this because you want to manually do some process when the capital form is submitted.
    def post(self,request,*args,**kwargs):
        form = self.get_form()
        if form.is_valid():
            target_cash_account = form.cleaned_data.get("cash_account")
            target_cash_account = CashAccount.objects.get(pk=target_cash_account.pk)
            target_cash_account.balance = target_cash_account.balance + form.cleaned_data.get("amount")
            target_cash_account.save()
            print('the form is valid')
            print(target_cash_account.pk)
            return self.form_valid(form)
    
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     # Pass the book to the template if needed
    #     context['book'] = Book.objects.get(pk=self.kwargs.get('pk'))
    #     print("printing book:", context["book"])
    #     return context
    
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})
    
class AddStakeholder(generic.edit.CreateView):
    model = Stakeholder
    form_class = StakeholderForm
    template_name = "accounting/add_stakeholder.html"

    # This sends to the form data on what book is this thing
    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     book_pk = self.kwargs.get('pk')
    #     book = Book.objects.get(pk=book_pk)
    #     kwargs['books'] = {'books': [book]}
    #     return kwargs

    # below preselected the book field of the model
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        # We do like this because it is a many to many field
        return {'books': [book]}
    

    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})
    
