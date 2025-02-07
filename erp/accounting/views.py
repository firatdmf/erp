from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse

# from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.views import View, generic

from operating.models import Product
from .models import EquityRevenue, ExpenseCategory, Income, IncomeCategory, Book, Asset, Invoice, InvoiceItem, Stakeholder,CashAccount, EquityCapital, EquityDivident,Transaction
from .models import EquityExpense, AccountBalance
# from .models import Expense, ExpenseCategory, Income, IncomeCategory
from .forms import EquityRevenueForm, ExpenseForm, IncomeForm, AssetForm, InvoiceForm,StakeholderForm, BookForm, EquityCapitalForm, EquityExpenseForm, EquityDividentForm, InvoiceItemForm, InvoiceItemFormSet, InTransferForm
from django.forms import modelformset_factory
from datetime import datetime
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required


from django.http import JsonResponse
from django.db.models import Q
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import decimal
from currency_converter import CurrencyConverter
import yfinance as yf
from decimal import Decimal
import math
import time


# Make this functional programming

@method_decorator(login_required, name='dispatch')
class index(generic.TemplateView):
    template_name = "accounting/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        books = Book.objects.all()
        context["books"] = books
        print(books)
        return context





@method_decorator(login_required, name='dispatch')
class CreateBook(generic.edit.CreateView):
    model = Book
    form_class = BookForm
    template_name = "accounting/create_book.html"
    # Takes you to the newly created book's detail page
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.object.pk})

@method_decorator(login_required, name='dispatch')
class BookDetail(generic.DetailView):
    model = Book
    template_name = "accounting/book_detail.html"
    context_object_name = "Book"

    def get_object(self):
        # Get the primary key from the URL
        pk = self.kwargs.get("pk")
        # Retrieve the Book object
    
        return get_object_or_404(Book, pk=pk)
    

    def get_exchange_rate(self,from_currency, to_currency):
        ticker = f"{from_currency}{to_currency}=X"
        data = yf.Ticker(ticker)
        exchange_rate = data.history(period="1d")['Close'][0]
        return Decimal(exchange_rate)

    def get_monthly_revenue_in_usd(self, start_date, end_date):
        book = self.get_object()
        revenues = EquityRevenue.objects.filter(book=book,date__gte=start_date, date__lt=end_date)
        total_revenue_usd = 0
        for revenue in revenues:
            if revenue.currency.code == 'USD':
                amount_in_usd = revenue.amount
            else:
                exchange_rate = self.get_exchange_rate(revenue.currency.code, 'USD')
                amount_in_usd = revenue.amount * exchange_rate
            total_revenue_usd += amount_in_usd
        return round(total_revenue_usd,2)
    
    def get_revenue_for_previous_months(self):
        now = timezone.now()
        first_day_of_current_month = datetime(now.year, now.month, 1)
        first_day_of_last_month = first_day_of_current_month - timedelta(days=1)
        first_day_of_last_month = datetime(first_day_of_last_month.year, first_day_of_last_month.month, 1)
        first_day_of_two_months_ago = first_day_of_last_month - timedelta(days=1)
        first_day_of_two_months_ago = datetime(first_day_of_two_months_ago.year, first_day_of_two_months_ago.month, 1)

        revenue_last_month = self.get_monthly_revenue_in_usd(first_day_of_last_month, first_day_of_current_month)
        revenue_two_months_ago = self.get_monthly_revenue_in_usd(first_day_of_two_months_ago, first_day_of_last_month)

        return revenue_two_months_ago, revenue_last_month
    
    def calculate_growth_rate(self):
        revenue_two_months_ago, revenue_last_month = self.get_revenue_for_previous_months()
        if revenue_last_month == 0:
            return 0  # Avoid division by zero
        growth_rate = ((revenue_last_month - revenue_two_months_ago) / revenue_last_month) * 100
        return round(growth_rate,2)
    
    def get_monthly_expenses_in_usd(self):
        book = self.get_object()
        # Get the first day of the current month
        now = timezone.now()
        first_day_of_month = datetime(now.year, now.month, 1)

        # Fetch all expenses from the beginning of the month until now
        expenses = EquityExpense.objects.filter(book=book,date__gte=first_day_of_month)

        total_expense_usd = 0
        for expense in expenses:
            if expense.currency.code == 'USD':
                amount_in_usd = expense.amount
            else:
                exchange_rate = self.get_exchange_rate(expense.currency.code, 'USD')
                amount_in_usd = expense.amount * exchange_rate
            total_expense_usd += amount_in_usd

        return round(total_expense_usd,2)
    

    def get_context_data(self,**kwargs):
        start_time = time.time()
        context = super().get_context_data(**kwargs)
        book = self.get_object()
        # ----------------------------
        # Below is for the total balance in cash accounts
        balance_usd = Decimal(CashAccount.objects.filter(book=book,currency=1).aggregate(Sum('balance'))['balance__sum'] or 0)
        balance_eur = Decimal(CashAccount.objects.filter(book=book,currency=2).aggregate(Sum('balance'))['balance__sum'] or 0)
        balance_try = Decimal(CashAccount.objects.filter(book=book,currency=3).aggregate(Sum('balance'))['balance__sum'] or 0)
        eur_to_usd = self.get_exchange_rate('EUR', 'USD')
        try_to_usd = self.get_exchange_rate('TRY', 'USD')

        balance_eur_in_usd = Decimal(balance_eur) * Decimal(eur_to_usd)
        balance_try_in_usd = Decimal(balance_try) * Decimal(try_to_usd)

        balance = Decimal(balance_usd) + Decimal(balance_eur_in_usd) + Decimal(balance_try_in_usd)
        balance = round(balance,2)

        context['balance'] = balance

        print(f'this is how long the balance equation takes: {(time.time() - start_time)}')

        # ----------------------------
        now = timezone.now()
        first_day_of_month = datetime(now.year, now.month, 1)
        day_of_today = datetime(now.year, now.month, now.day)
        context['revenue'] = self.get_monthly_revenue_in_usd(first_day_of_month,day_of_today)
        context['expense'] = self.get_monthly_expenses_in_usd()
        context['burn'] = context['revenue'] - context['expense']
        # Below is number of months you can survive, rounds it down to 2 decimals
        avg_burn = -1000
        context['runway'] = round(( context['balance'] / abs(avg_burn)),1)
        context['growth_rate'] = self.calculate_growth_rate()
        context['default_alive'] = ""
        # print(f"Balance: {balance}")
        # book = Book.objects.get(pk=self.kwargs.get('pk'))
        book = self.get_object()
        # print(type(book))
        context['Stakeholders'] = Stakeholder.objects.filter(books=book)
        print(type(Stakeholder.objects.filter(books=book)))
        # print(context['Stakeholders'])
        print(f'this is how long the execution takes: {(time.time() - start_time)}')
        return context


@method_decorator(login_required, name='dispatch')
class CategorySearchView(View):
    def get(self, request):
        query = request.GET.get("query", "")
        if query:
            categories = ExpenseCategory.objects.filter(name__icontains=query)
        else:
            categories = ExpenseCategory.objects.none()
        data = [{"id": category.id, "name": category.name} for category in categories]
        return JsonResponse(data, safe=False)

@method_decorator(login_required, name='dispatch')
class SalesView(generic.TemplateView):
    template_name = "accounting/sales_report.html"


# not sure if I need this
@method_decorator(login_required, name='dispatch')
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

@method_decorator(login_required, name='dispatch')
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

            # new_asset = Asset.objects.create(book = self.kwargs.get('pk'), )
            return self.form_valid(form)
    
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     # Pass the book to the template if needed
    #     context['book'] = Book.objects.get(pk=self.kwargs.get('pk'))
    #     print("printing book:", context["book"])
    #     return context
    
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})
    
@method_decorator(login_required, name='dispatch')
class AddEquityRevenue(generic.edit.CreateView):
    model = EquityRevenue
    form_class = EquityRevenueForm
    template_name = "accounting/add_equity_revenue.html"

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        kwargs['book'] = book
        return kwargs
    
    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        # By default make the currency US Dollars (which is 1)
        return {'book': book, 'currency':1}
    

    # You do this because you want to manually do some process when the expense form is submitted.
    def post(self,request,*args,**kwargs):
        print('you sent a post request')
        form = self.get_form()
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        latest_revenue_item = EquityRevenue.objects.filter(book=book).latest('pk')
        type_pk = latest_revenue_item.pk + 1
        if form.is_valid():
            print("hey the form is valid man!!!")


            # Get the selected cash account from the form
            target_cash_account = form.cleaned_data.get("cash_account")
            target_cash_account = CashAccount.objects.get(pk=target_cash_account.pk)
            # Update the balance of the cash account
            target_cash_account.balance = target_cash_account.balance + form.cleaned_data.get("amount")
            
             # Save the updated cash account
            target_cash_account.save()

            currency = form.cleaned_data.get("currency")
            # You need error handling here.
            transaction = Transaction(book=book,value = form.cleaned_data.get("amount"),currency=currency,type="revenue", account =target_cash_account, type_pk =type_pk , account_balance = target_cash_account.balance )
            transaction.save()

            # # All cash accounts combined
            # total_cash = CashAccount.objects.filter(book=kwargs['book'])

             # Now you need to update the form instance before saving it
            # Create the model instance but don't save it yet
            my_form = form.save(commit=False)
            # my_form.account_balance = target_cash_account.balance
            # my_form.account_currency = target_cash_account.currency
            my_form.save()
            # my_field_value = form.cleaned_data.get('balance')
            # form.cleaned_data['balance'] = target_cash_account.balance
            # new_asset = Asset.objects.create(book = self.kwargs.get('pk'), )
            # print('the form is valid')
            # print(target_cash_account.pk)

            return self.form_valid(form)
        else:
            for field in form:
                print("Field Error:", field.name,  field.errors)
    
    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})
    

@method_decorator(login_required, name='dispatch')
class AddStakeholder(generic.edit.CreateView):
    model = Stakeholder
    form_class = StakeholderForm
    template_name = "accounting/add_stakeholder.html"

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     book_pk = self.kwargs.get('pk')
    #     book = Book.objects.get(pk=book_pk)
    #     print(book)
    #     kwargs['book'] = [book_pk]
    #     return kwargs
    
    def form_valid(self, form):
       
        self.object = form.save(commit=False) # Save the stakeholder instance without committing to the database
        self.object.save() # Save the stakeholder instance first
        # Add the selected book to the stakeholder's books field (ManyToMany)
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        self.object.books.add(book)  # Link the stakeholder to the book
        return super().form_valid(form)
  
    # # below preselected the book field of the capital model
    # def get_initial(self):
    #     # Get the book by primary key from the URL
    #     book_pk = self.kwargs.get('pk')
    #     book = Book.objects.get(pk=book_pk)
    #     # Set the initial value of the book field to the book retrieved
    #     return {'books': [book]}
    

    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})
    

@method_decorator(login_required, name='dispatch')
class EquityExpenseList(generic.ListView):
    model = EquityExpense
    template_name = "accounting/equity_expense_list.html"

@method_decorator(login_required, name='dispatch')
class TransactionList(generic.ListView):
    model =Transaction
    template_name = "accounting/transaction_list.html"


@method_decorator(login_required, name='dispatch')
class PayEquityDivident(generic.edit.CreateView):
    model = EquityDivident
    form_class = EquityDividentForm
    template_name = "accounting/pay_equity_divident.html"

     # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        kwargs['book'] = book
        return kwargs
    
    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        # By default make the currency US Dollars (which is 1)
        return {'book': book, 'currency':1}
    
    # You do this because you want to manually do some process when the expense form is submitted.
    def post(self,request,*args,**kwargs):
        form = self.get_form()
        if form.is_valid():
            # Get the selected cash account from the form
            target_cash_account = form.cleaned_data.get("cash_account")
            target_cash_account = CashAccount.objects.get(pk=target_cash_account.pk)
            # Update the balance of the cash account
            target_cash_account.balance = target_cash_account.balance - form.cleaned_data.get("amount")
            
             # Save the updated cash account
            target_cash_account.save()




            # # All cash accounts combined
            # total_cash = CashAccount.objects.filter(book=kwargs['book'])

             # Now you need to update the form instance before saving it
            # Create the model instance but don't save it yet
            my_form = form.save(commit=False)
            my_form.account_balance = target_cash_account.balance
            my_form.account_currency = target_cash_account.currency
            my_form.save()
            # my_field_value = form.cleaned_data.get('balance')
            # form.cleaned_data['balance'] = target_cash_account.balance
            # new_asset = Asset.objects.create(book = self.kwargs.get('pk'), )
            # print('the form is valid')
            # print(target_cash_account.pk)
            return self.form_valid(form)
    
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})
    






@method_decorator(login_required, name='dispatch')
class AddEquityExpense(generic.edit.CreateView):
    model = EquityExpense
    form_class = EquityExpenseForm
    template_name = "accounting/add_equity_expense.html"

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        kwargs['book'] = book
        return kwargs
    
    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        # By default make the currency US Dollars (which is 1)
        return {'book': book, 'currency':1}
    

    # below stops the form after it submitted so we can add additional operations
    # def form_valid(self, form):
    #     self.object = form.save(commit=False) # Save the expense instance without committing to the database
    #     self.object.save() # Save the expense instance first

    #     # get the book pk from the url
    #     book_pk = self.kwargs.get('pk')
    #     # select that specific book
    #     book = Book.objects.get(pk=book_pk)
    #     return super().form_valid(form)

    # You do this because you want to manually do some process when the expense form is submitted.
    def post(self,request,*args,**kwargs):
        form = self.get_form()
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        latest_revenue_item = EquityExpense.objects.filter(book=book).latest('pk')
        type_pk = latest_revenue_item.pk + 1
        if form.is_valid():
            # Get the selected cash account from the form
            target_cash_account = form.cleaned_data.get("cash_account")
            target_cash_account = CashAccount.objects.get(pk=target_cash_account.pk)
            # Update the balance of the cash account
            target_cash_account.balance = target_cash_account.balance - form.cleaned_data.get("amount")
            
             # Save the updated cash account
            target_cash_account.save()

            currency = form.cleaned_data.get("currency")
            transaction = Transaction(book=book,value = (form.cleaned_data.get("amount")),currency=currency,type="expense", account = target_cash_account, type_pk = type_pk, account_balance = target_cash_account.balance )
            transaction.save()


            # # All cash accounts combined
            # total_cash = CashAccount.objects.filter(book=kwargs['book'])

             # Now you need to update the form instance before saving it
            # Create the model instance but don't save it yet
            my_form = form.save(commit=False)
            my_form.account_balance = target_cash_account.balance
            my_form.account_currency = target_cash_account.currency
            my_form.save()
            # my_field_value = form.cleaned_data.get('balance')
            # form.cleaned_data['balance'] = target_cash_account.balance
            # new_asset = Asset.objects.create(book = self.kwargs.get('pk'), )
            # print('the form is valid')
            # print(target_cash_account.pk)
            return self.form_valid(form)
    
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})
    
@method_decorator(login_required, name='dispatch')
class InvoiceCreateView(generic.CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'accounting/create_invoice.html'
    success_url = reverse_lazy('operating:index')

    def get_context_data(self, **kwargs):
        # Add the invoice form and formset for items
        context = super().get_context_data(**kwargs)
        InvoiceItemFormSet = modelformset_factory(InvoiceItem, form=InvoiceItemForm, extra=1)
        context['item_formset'] = InvoiceItemFormSet(queryset=InvoiceItem.objects.none())
        return context

    def form_valid(self,form):
        invoice = form.save()
        # Now that the invoice is saved, it has a primary key
        # Get the formset for invoice items
        item_formset = InvoiceItemFormSet(self.request.POST)
        # products = self.request.POST.getlist('products')
        if item_formset.is_valid():
            total_amount = 0  # Initialize total_amount to 0
            items_to_save = []  # Collect InvoiceItem instances to save later
            # For each form in the formset, create an InvoiceItem entry
            for item_form in item_formset:
                product = item_form.cleaned_data.get('product')
                quantity = item_form.cleaned_data.get('quantity')
                price = item_form.cleaned_data.get('price')
                if product and quantity is not None and price is not None:
                    item = InvoiceItem(
                        invoice=invoice,
                        product=product,
                        quantity=quantity,
                        price=price
                    )
                    items_to_save.append(item)
                    # Accumulate total amount
                    total_amount += quantity * price

                    
            InvoiceItem.objects.bulk_create(items_to_save)
            invoice.total_amount = total_amount
            invoice.save()  # Save the updated invoice
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class MakeInTransfer(generic.edit.FormView):
    form_class = InTransferForm
    template_name = "accounting/make_in_transfer.html"

    success_url = reverse_lazy('books/2/make_in_transfer')  # Replace 'success_page' with your success URL name


    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        kwargs['book'] = book
        return kwargs
    

    def form_valid(self, form):
        # Process the form data
        amount = form.cleaned_data['amount']
        date = form.cleaned_data['date']
        from_cash_account = form.cleaned_data['from_cash_account']
        from_cash_account = CashAccount.objects.get(pk=from_cash_account.pk)
        from_cash_account_new_balance = from_cash_account.balance - amount
        from_cash_account.balance = from_cash_account_new_balance
        from_cash_account.save()

        transaction1 = Transaction(book=from_cash_account.book,value = amount,currency=from_cash_account.currency,type="transfer", account = from_cash_account, type_pk = None, account_balance= from_cash_account_new_balance )
        transaction1.save()
        print(f"from cash account is: {from_cash_account}")
        to_cash_account = form.cleaned_data['to_cash_account']
        to_cash_account = CashAccount.objects.get(pk=to_cash_account.pk)
        to_cash_account_new_balance = to_cash_account.balance + amount
        to_cash_account.balance = to_cash_account_new_balance
        to_cash_account.save()

        transaction2 = Transaction(book=to_cash_account.book,value = amount,currency=to_cash_account.currency,type="transfer", account = to_cash_account, type_pk = None, account_balance = to_cash_account_new_balance )
        transaction2.save()
        # Add your processing logic here
        return super().form_valid(form)
    

@method_decorator(login_required, name='dispatch')
class AccountBalance(generic.CreateView):
    model = AccountBalance
    fields = '__all__'
    template_name = 'accounting/account_balance.html'

    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})

    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {'book': book}

    # def form_valid(self, form):
    #     # Process the form data
    #     book_pk = self.kwargs.get('pk')
    #     book = Book.objects.get(pk=book_pk)
    #     cash_account = form.cleaned_data['cash_account']
    #     cash_account = CashAccount.objects.get(pk=cash_account.pk)
    #     cash_account.balance = form.cleaned_data['balance']
    #     cash_account.save()
    #     return super().form_valid(form)