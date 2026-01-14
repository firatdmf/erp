from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse

# from django.views.generic import TemplateView
from django.urls import reverse_lazy, reverse
from django.views import View, generic
from django.db import transaction, IntegrityError, DatabaseError, OperationalError

# from operating.models import Product

from .models import *

# from .models import Expense, ExpenseCategory, Income, IncomeCategory
from .forms import *
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

# import yfinance as yf
from decimal import Decimal
import math
import time
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType

# add functions here


def get_total_base_currency_balance(book_pk):
    base_currency = get_base_currency()
    total = Decimal("0.00")

    for currency_category in CurrencyCategory.objects.all():
        # sum all accounts of this currency
        cash_accounts = CashAccount.objects.filter(
            book=book_pk,
            currency=currency_category,
        )
        balance = sum(ca.balance for ca in cash_accounts)

        if balance == 0:
            continue

        if currency_category != base_currency:
            from .services import get_exchange_rate

            rate = get_exchange_rate(currency_category.code, base_currency.code)
            if not rate:
                raise ValidationError(
                    {
                        "currency_rate": f"Failed to get rate {currency_category.code} → {base_currency.code}"
                    }
                )
            balance = Decimal(balance)
            rate = Decimal(rate)

            total += (balance * rate).quantize(Decimal("0.01"))
        else:
            balance = Decimal(balance)
            total += balance

    return total


# def get_exchange_rate(self, from_currency, to_currency):
#     ticker = f"{from_currency}{to_currency}=X"
#     data = yf.Ticker(ticker)
#     exchange_rate = data.history(period="1d")["Close"][0]
#     return Decimal(exchange_rate)


@method_decorator(login_required, name="dispatch")
class index(generic.TemplateView):
    template_name = "accounting/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        books = Book.objects.all()
        context["books"] = books
        return context


@method_decorator(login_required, name="dispatch")
class CreateBook(generic.edit.CreateView):
    model = Book
    form_class = BookForm
    template_name = "accounting/create_book.html"

    # Takes you to the newly created book's detail page
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.object.pk})


@method_decorator(login_required, name="dispatch")
class BookDetail(generic.DetailView):
    model = Book
    template_name = "accounting/book_detail.html"
    context_object_name = "book"

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context[""] =
    #     return context

    def get_object(self):
        # Get the primary key from the URL
        pk = self.kwargs.get("pk")
        # Retrieve the Book object

        return get_object_or_404(Book, pk=pk)

    # def get_exchange_rate(self, from_currency, to_currency):
    #     ticker = f"{from_currency}{to_currency}=X"
    #     data = yf.Ticker(ticker)
    #     exchange_rate = data.history(period="1d")["Close"][0]
    #     return Decimal(exchange_rate)

    # def get_monthly_revenue_in_usd(self, start_date, end_date):
    #     book = self.get_object()
    #     revenues = EquityRevenue.objects.filter(
    #         book=book, date__gte=start_date, date__lt=end_date
    #     )
    #     total_revenue_usd = 0
    #     for revenue in revenues:
    #         if revenue.currency.code == "USD":
    #             amount_in_usd = revenue.amount
    #         else:
    #             exchange_rate = self.get_exchange_rate(revenue.currency.code, "USD")
    #             amount_in_usd = revenue.amount * exchange_rate
    #         total_revenue_usd += amount_in_usd
    #     return round(total_revenue_usd, 2)

    # def get_revenue_for_previous_months(self):
    #     now = timezone.now()
    #     first_day_of_current_month = datetime(now.year, now.month, 1)
    #     first_day_of_last_month = first_day_of_current_month - timedelta(days=1)
    #     first_day_of_last_month = datetime(
    #         first_day_of_last_month.year, first_day_of_last_month.month, 1
    #     )
    #     first_day_of_two_months_ago = first_day_of_last_month - timedelta(days=1)
    #     first_day_of_two_months_ago = datetime(
    #         first_day_of_two_months_ago.year, first_day_of_two_months_ago.month, 1
    #     )

    #     revenue_last_month = self.get_monthly_revenue_in_usd(
    #         first_day_of_last_month, first_day_of_current_month
    #     )
    #     revenue_two_months_ago = self.get_monthly_revenue_in_usd(
    #         first_day_of_two_months_ago, first_day_of_last_month
    #     )

    #     return revenue_two_months_ago, revenue_last_month

    # def calculate_growth_rate(self):
    #     revenue_two_months_ago, revenue_last_month = (
    #         self.get_revenue_for_previous_months()
    #     )
    #     if revenue_last_month == 0:
    #         return 0  # Avoid division by zero
    #     growth_rate = (
    #         (revenue_last_month - revenue_two_months_ago) / revenue_last_month
    #     ) * 100
    #     return round(growth_rate, 2)

    # def get_monthly_expenses_in_usd(self):
    #     book = self.get_object()
    #     # Get the first day of the current month
    #     now = timezone.now()
    #     first_day_of_month = datetime(now.year, now.month, 1)

    #     # Fetch all expenses from the beginning of the month until now
    #     expenses = EquityExpense.objects.filter(book=book, date__gte=first_day_of_month)

    #     total_expense_usd = 0
    #     for expense in expenses:
    #         if expense.currency.code == "USD":
    #             amount_in_usd = expense.amount
    #         else:
    #             exchange_rate = self.get_exchange_rate(expense.currency.code, "USD")
    #             amount_in_usd = expense.amount * exchange_rate
    #         total_expense_usd += amount_in_usd

    #     return round(total_expense_usd, 2)

    # def get_context_data(self, **kwargs):
    #     start_time = time.time()
    #     context = super().get_context_data(**kwargs)
    #     book = self.get_object()
    #     # ----------------------------
    #     # Below is for the total balance in cash accounts
    #     balance_usd = Decimal(
    #         CashAccount.objects.filter(book=book, currency=1).aggregate(Sum("balance"))[
    #             "balance__sum"
    #         ]
    #         or 0
    #     )
    #     balance_eur = Decimal(
    #         CashAccount.objects.filter(book=book, currency=2).aggregate(Sum("balance"))[
    #             "balance__sum"
    #         ]
    #         or 0
    #     )
    #     balance_try = Decimal(
    #         CashAccount.objects.filter(book=book, currency=3).aggregate(Sum("balance"))[
    #             "balance__sum"
    #         ]
    #         or 0
    #     )
    #     eur_to_usd = self.get_exchange_rate("EUR", "USD")
    #     try_to_usd = self.get_exchange_rate("TRY", "USD")

    #     balance_eur_in_usd = Decimal(balance_eur) * Decimal(eur_to_usd)
    #     balance_try_in_usd = Decimal(balance_try) * Decimal(try_to_usd)

    #     balance = (
    #         Decimal(balance_usd)
    #         + Decimal(balance_eur_in_usd)
    #         + Decimal(balance_try_in_usd)
    #     )
    #     balance = round(balance, 2)

    #     context["balance"] = balance

    #     print(
    #         f"this is how long the balance equation takes: {(time.time() - start_time)}"
    #     )

    #     # ----------------------------
    #     now = timezone.now()
    #     first_day_of_month = datetime(now.year, now.month, 1)
    #     day_of_today = datetime(now.year, now.month, now.day)
    #     context["revenue"] = self.get_monthly_revenue_in_usd(
    #         first_day_of_month, day_of_today
    #     )
    #     context["expense"] = self.get_monthly_expenses_in_usd()
    #     context["burn"] = context["revenue"] - context["expense"]
    #     # Below is number of months you can survive, rounds it down to 2 decimals
    #     avg_burn = -1000
    #     context["runway"] = round((context["balance"] / abs(avg_burn)), 1)
    #     context["growth_rate"] = self.calculate_growth_rate()
    #     context["default_alive"] = ""
    #     book = self.get_object()
    #     stakeholders = StakeholderBook.objects.filter(book_id=book.pk)
    #     context["Stakeholders"] = stakeholders
    #     print(f"this is how long the execution takes: {(time.time() - start_time)}")
    #     return context


@method_decorator(login_required, name="dispatch")
class AddStakeholderBook(generic.edit.CreateView):
    model = StakeholderBook
    form_class = StakeholderBookForm
    template_name = "accounting/add_stakeholderbook.html"

    # below preselected the book field of the capital model
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {"book": book}

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:book_detail", kwargs={"pk": self.kwargs.get("pk")}
        )


# ------------------------------------------------------------------------------------------------
# equity functions:
@transaction.atomic
def handle_equity_transaction(
    book, amount, currency, equity_instance, equity_pk, cash_account
):
    import time

    # 1 Add Transaction
    # 2 Adjust Asset Cash
    # 3 adjust cashaccount balance
    start_time = time.time()
    is_amount_positive = True
    # 1
    cash_account = CashAccount.objects.get(pk=cash_account.pk)
    if isinstance(equity_instance, (EquityCapital, EquityRevenue)):
        cash_account.balance += amount
        is_amount_positive = True
    elif isinstance(equity_instance, (EquityExpense, EquityDivident)):
        cash_account.balance -= amount
        is_amount_positive = False
    else:
        raise ValidationError({"cash_account": "cash_account balance failed to update"})
    cash_account.save(update_fields=["balance"])

    print("the time it took:", "--- %s seconds ---" % (time.time() - start_time))

    # # 2
    # asset_cash, created = AssetCash.objects.get_or_create(book=book, currency=currency)
    # if created:
    #     asset_cash.balance = 0
    # asset_cash.balance += amount
    # asset_cash.save(update_fields=["balance"])

    # 3
    content_type = ContentType.objects.get_for_model(equity_instance)
    cash_transaction_entry = CashTransactionEntry.objects.create(
        book=book,
        content_type=content_type,
        content_pk=equity_pk,
        amount=amount,
        is_amount_positive=is_amount_positive,
        currency=currency,
        cash_account=cash_account,
        cash_account_balance=cash_account.balance,
    )
    print("the time2 it took:", "--- %s seconds ---" % (time.time() - start_time))
    print("all done")
    return True


def handle_payable_and_receivable(
    book, amount, currency, model_instance, model_pk, cash_account
):
    is_amount_positive = False  # initialize the value
    if isinstance(model_instance, AssetAccountsReceivable):
        is_amount_positive = True
    elif isinstance(model_instance, LiabilityAccountsPayable):
        is_amount_positive = False

    content_type = ContentType.objects.get_for_model(model_instance)
    cash_transaction_entry = CashTransactionEntry.objects.create(
        book=book,
        content_type=content_type,
        content_pk=model_pk,
        amount=amount,
        is_amount_positive=is_amount_positive,
        currency=currency,
        cash_account=cash_account,
        cash_account_balance=cash_account.balance,
    )


# -------


@method_decorator(login_required, name="dispatch")
class AddEquityCapital(generic.edit.CreateView):
    model = EquityCapital
    form_class = EquityCapitalForm
    template_name = "accounting/add_equity_capital.html"

    # # This sends to the form data the book we are in. We need this so we can show the cash accounts only associated with this book.
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below pre-selects the book field of the capital model in the form
    # below is available in CreateView and UpdateViews
    # Usage: It returns a dictionary where the keys are the form field names and the values are the initial data for those fields.
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        return {
            "book": book,
        }

    # revert back all db changes if any errors while in form_valid
    @transaction.atomic
    def form_valid(self, form):

        # get the book pk from the url:
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)

        # get the capital amount from form post data
        amount = form.cleaned_data.get("amount")
        cash_account = form.cleaned_data.get("cash_account")
        if not cash_account:
            form.add_error("cash_account", "Please select a valid cash account.")
            return self.form_invalid(form)

        # Set the currency to the deposited_cash_account's currency
        currency = cash_account.currency

        # Example: update stakeholder shares
        member = form.cleaned_data["member"]
        # a stakeholderbook object has a book and a member
        try:
            stakeholderbook = StakeholderBook.objects.get(member=member, book=book)
            stakeholderbook.shares += form.cleaned_data["new_shares_issued"]
            stakeholderbook.save(update_fields=["shares"])
        except ObjectDoesNotExist:
            form.add_error("member", "Couldn't fetch the member properly")
            return self.form_invalid(form)

        # get the new created object (EquityCapital)
        # form.save(commit=False) creates a model instance before saving it to the database
        self.object = form.save(commit=False)
        self.object.currency = currency
        # now save to the database
        self.object.save()
        equity_pk = self.object.pk
        equity_instance = self.object
        result = handle_equity_transaction(
            book, amount, currency, equity_instance, equity_pk, cash_account
        )
        if result is not True:
            form.add_error(None, "Form error: in handle_equity_transaction function")
            return self.form_invalid(form)

        # This method saves the form instance to the database and then redirects the user to a success URL.
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse(
            "accounting:add_equity_capital", kwargs={"pk": self.kwargs.get("pk")}
        )

    # what happens when form validation fails
    def form_invalid(self, form):
        # Optionally log errors here
        for field in form:
            for error in field.errors:
                print(f"Error in field {field.name}: {error}")
        for error in form.non_field_errors():
            print(f"Form error: {error}")
        return super().form_invalid(form)


@method_decorator(login_required, name="dispatch")
class AddEquityRevenue(generic.edit.CreateView):
    model = EquityRevenue
    form_class = EquityRevenueForm
    template_name = "accounting/add_equity_revenue.html"

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {
            "book": book,
        }

    # revert back all db changes if any errors while in form_valid
    @transaction.atomic
    def form_valid(self, form):

        # get the book pk from the url:
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # revenue amount
        amount = form.cleaned_data.get("amount")

        # Get the selected cash account from the form
        cash_account = form.cleaned_data.get("cash_account")
        if not cash_account:
            form.add_error("cash_account", "Please select a valid cash account.")
            return self.form_invalid(form)
        # Set the currency to the deposited_cash_account's currency
        currency = cash_account.currency
        self.object = form.save(commit=False)
        self.object.currency = currency
        self.object.save()
        equity_pk = self.object.pk
        equity_instance = self.object
        result = handle_equity_transaction(
            book, amount, currency, equity_instance, equity_pk, cash_account
        )
        if result is not True:
            form.add_error(None, "Form error: in handle_equity_transaction function")
            return self.form_invalid(form)

        # This method saves the form instance to the database and then redirects the user to a success URL.
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse(
            "accounting:add_equity_revenue", kwargs={"pk": self.kwargs.get("pk")}
        )

    # what happens when form validation fails
    def form_invalid(self, form):
        # Optionally log errors here
        for field in form:
            for error in field.errors:
                print(f"Error in field {field.name}: {error}")
        for error in form.non_field_errors():
            print(f"Form error: {error}")
        return super().form_invalid(form)


@method_decorator(login_required, name="dispatch")
class AddEquityExpense(generic.edit.CreateView):
    model = EquityExpense
    form_class = EquityExpenseForm
    template_name = "accounting/add_equity_expense.html"

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below pre-selecting the book field in the form according to the pk in the url
    # get initial is a function that is applicable to update and create views like these forms.
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        # By default make the currency US Dollars (which is 1)
        return {"book": book}

    @transaction.atomic
    def form_valid(self, form):
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)

        # expense amount
        amount = form.cleaned_data.get("amount")
        cash_account = form.cleaned_data.get("cash_account")
        if not cash_account:
            form.add_error("cash_account", "Please select a valid cash account.")
            return self.form_invalid(form)
            # Set the currency to the deposited_cash_account's currency
        currency = cash_account.currency
        self.object = form.save(commit=False)
        self.object.currency = currency
        self.object.save()
        equity_pk = self.object.pk
        equity_instance = self.object
        result = handle_equity_transaction(
            book, amount, currency, equity_instance, equity_pk, cash_account
        )
        if result is not True:
            form.add_error(None, "Form error: in handle_equity_transaction function")
            return self.form_invalid(form)

        # This method saves the form instance to the database and then redirects the user to a success URL.
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse(
            "accounting:add_equity_expense", kwargs={"pk": self.kwargs.get("pk")}
        )

    # what happens when form validation fails
    def form_invalid(self, form):
        # Optionally log errors here
        for field in form:
            for error in field.errors:
                print(f"Error in field {field.name}: {error}")
        for error in form.non_field_errors():
            print(f"Form error: {error}")
        return super().form_invalid(form)


@method_decorator(login_required, name="dispatch")
class AddEquityDivident(generic.edit.CreateView):
    model = EquityDivident
    form_class = EquityDividentForm
    template_name = "accounting/add_equity_divident.html"

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {"book": book}

    @transaction.atomic
    def form_valid(self, form):
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)

        # divident amount given to stakeholder
        amount = form.cleaned_data.get("amount")
        cash_account = form.cleaned_data.get("cash_account")
        if not cash_account:
            form.add_error("cash_account", "Please select a valid cash account.")
            return self.form_invalid(form)
            # Set the currency to the deposited_cash_account's currency
        currency = cash_account.currency
        self.object = form.save(commit=False)
        self.object.currency = currency
        self.object.save()
        equity_pk = self.object.pk
        equity_instance = self.object
        result = handle_equity_transaction(
            book, amount, currency, equity_instance, equity_pk, cash_account
        )
        if result is not True:
            form.add_error(None, "Form error: in handle_equity_transaction function")
            return self.form_invalid(form)

        # This method saves the form instance to the database and then redirects the user to a success URL.
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse(
            "accounting:add_equity_divident", kwargs={"pk": self.kwargs.get("pk")}
        )

    # what happens when form validation fails
    def form_invalid(self, form):
        # Optionally log errors here
        for field in form:
            for error in field.errors:
                print(f"Error in field {field.name}: {error}")
        for error in form.non_field_errors():
            print(f"Form error: {error}")
        return super().form_invalid(form)


@method_decorator(login_required, name="dispatch")
class AddAccountsReceivable(generic.edit.CreateView):
    model = AssetAccountsReceivable
    form_class = AssetAccountsReceivableForm
    template_name = "accounting/add_accounts_receivable.html"
    # fields = "__all__"

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved, and currency to usd
        return {"book": book, "currency": 1}

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:add_accounts_receivable", kwargs={"pk": self.kwargs.get("pk")}
        )

    # def get_form_kwargs(self):
    #     book =
    #     self.kwargs['book'] = book
    #     return super().get_form_kwargs()


@method_decorator(login_required, name="dispatch")
class AddAccountsPayable(generic.edit.CreateView):
    model = LiabilityAccountsPayable
    form_class = LiabilityAccountsPayableForm
    template_name = "accounting/add_accounts_payable.html"
    # fields = "__all__"

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved, and currency to usd
        return {"book": book, "currency": 1}

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:add_accounts_payable", kwargs={"pk": self.kwargs.get("pk")}
        )


# do not remember what this did
@method_decorator(login_required, name="dispatch")
class CategorySearchView(View):
    def get(self, request):
        query = request.GET.get("query", "")
        if query:
            categories = ExpenseCategory.objects.filter(name__icontains=query)
        else:
            categories = ExpenseCategory.objects.none()
        data = [{"id": category.id, "name": category.name} for category in categories]
        return JsonResponse(data, safe=False)


@method_decorator(login_required, name="dispatch")
class SalesView(generic.TemplateView):
    template_name = "accounting/sales_report.html"


@method_decorator(login_required, name="dispatch")
class EquityExpenseList(generic.ListView):
    model = EquityExpense
    template_name = "accounting/equity_expense_list.html"


@method_decorator(login_required, name="dispatch")
class CashTransactionEntryList(generic.ListView):
    model = CashTransactionEntry
    template_name = "accounting/cash_transaction_entry_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_currency_symbol"] = str(get_base_currency().symbol)
        return context

    def get_queryset(self):
        book_pk = self.kwargs.get("pk")
        return CashTransactionEntry.objects.filter(book=book_pk)


# @method_decorator(login_required, name='dispatch')
# class InvoiceCreateView(generic.CreateView):
#     model = Invoice
#     form_class = InvoiceForm
#     template_name = 'accounting/create_invoice.html'
#     success_url = reverse_lazy('operating:index')

#     def get_context_data(self, **kwargs):
#         # Add the invoice form and formset for items
#         context = super().get_context_data(**kwargs)
#         InvoiceItemFormSet = modelformset_factory(InvoiceItem, form=InvoiceItemForm, extra=1)
#         context['item_formset'] = InvoiceItemFormSet(queryset=InvoiceItem.objects.none())
#         return context

#     def form_valid(self,form):
#         invoice = form.save()
#         # Now that the invoice is saved, it has a primary key
#         # Get the formset for invoice items
#         item_formset = InvoiceItemFormSet(self.request.POST)
#         # products = self.request.POST.getlist('products')
#         if item_formset.is_valid():
#             total_amount = 0  # Initialize total_amount to 0
#             items_to_save = []  # Collect InvoiceItem instances to save later
#             # For each form in the formset, create an InvoiceItem entry
#             for item_form in item_formset:
#                 product = item_form.cleaned_data.get('product')
#                 quantity = item_form.cleaned_data.get('quantity')
#                 price = item_form.cleaned_data.get('price')
#                 if product and quantity is not None and price is not None:
#                     item = InvoiceItem(
#                         invoice=invoice,
#                         product=product,
#                         quantity=quantity,
#                         price=price
#                     )
#                     items_to_save.append(item)
#                     # Accumulate total amount
#                     total_amount += quantity * price


#             InvoiceItem.objects.bulk_create(items_to_save)
#             invoice.total_amount = total_amount
#             invoice.save()  # Save the updated invoice
#         return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class MakeInTransfer(generic.edit.CreateView):
    model = InTransfer
    form_class = InTransferForm
    template_name = "accounting/make_in_transfer.html"

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {"book": book}

    @transaction.atomic
    def form_valid(self, form):
        # Process the form data
        # get the book pk from the url:
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # transfer amount
        amount = form.cleaned_data["amount"]

        from_cash_account = form.cleaned_data["from_cash_account"]
        to_cash_account = form.cleaned_data["to_cash_account"]
        if not from_cash_account or not to_cash_account:
            form.add_error(
                "Cash Account",
                "Please select a valid cash accounts for the in transfer.",
            )
            return self.form_invalid(form)
        # from_cash_account = CashAccount.objects.get(pk=from_cash_account.pk)

        from_cash_account.balance -= amount
        from_cash_account.save(update_fields=["balance"])

        to_cash_account.balance += amount
        to_cash_account.save(update_fields=["balance"])

        self.object = form.save(commit=False)
        self.object.currency = from_cash_account.currency
        self.object = form.save()

        content_instance = self.object
        content_pk = self.object.pk
        content_type = ContentType.objects.get_for_model(content_instance)

        from_cash_account_transaction_entry = CashTransactionEntry.objects.create(
            book=book,
            content_type=content_type,
            content_pk=content_pk,
            amount=amount,
            is_amount_positive=False,
            currency=from_cash_account.currency,
            cash_account=from_cash_account,
        )

        to_cash_account_transaction_entry = CashTransactionEntry.objects.create(
            book=book,
            content_type=content_type,
            content_pk=content_pk,
            amount=amount,
            is_amount_positive=True,
            currency=to_cash_account.currency,
            cash_account=to_cash_account,
        )
        # cash_transaction_entry_2.save()
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:make_in_transfer", kwargs={"pk": self.kwargs.get("pk")}
        )

    def form_invalid(self, form):
        # Optionally log errors here
        for field in form:
            for error in field.errors:
                print(f"Error in field {field.name}: {error}")
        for error in form.non_field_errors():
            print(f"Form error: {error}")
        return super().form_invalid(form)


@method_decorator(login_required, name="dispatch")
class MakeCurrencyExchange(generic.edit.FormView):
    form_class = CurrencyExchangeForm
    template_name = "accounting/make_currency_exchange.html"

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:make_currency_exchange", kwargs={"pk": self.kwargs.get("pk")}
        )

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved, and currency to usd
        return {"book": book}

    @transaction.atomic
    def form_valid(self, form):
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Process the form data
        from_amount = form.cleaned_data["from_amount"]
        to_amount = form.cleaned_data["to_amount"]

        from_cash_account = form.cleaned_data["from_cash_account"]
        from_cash_account.balance -= from_amount
        from_cash_account.save(update_fields=["balance"])

        to_cash_account = form.cleaned_data["to_cash_account"]
        to_cash_account.balance += to_amount
        to_cash_account.save(update_fields=["balance"])

        self.object = form.save()

        content_instance = self.object
        content_pk = self.object.pk
        content_type = ContentType.objects.get_for_model(content_instance)

        from_cash_account_transaction_entry = CashTransactionEntry.objects.create(
            book=book,
            content_type=content_type,
            content_pk=content_pk,
            amount=from_amount,
            is_amount_positive=False,
            currency=from_cash_account.currency,
            cash_account=from_cash_account,
        )

        to_cash_account_transaction_entry = CashTransactionEntry.objects.create(
            book=book,
            content_type=content_type,
            content_pk=content_pk,
            amount=to_amount,
            is_amount_positive=True,
            currency=to_cash_account.currency,
            cash_account=to_cash_account,
        )

        # Add your processing logic here
        return super().form_valid(form)


# below are added after august 4, 2025 and for the new cogs system

# accounting.py (or similar location)


class CreateAssetInventoryRawMaterialGood(generic.CreateView):
    model = AssetInventoryRawMaterial
    form_class = AssetInventoryRawMaterialGoodForm
    template_name = "accounting/create_asset_inventory_raw_material_good.html"
    success_url = reverse_lazy(
        "accounting:create_asset_inventory_raw_material_good", kwargs={"pk": "pk"}
    )

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below preselected the book field of the capital model (independent of the above function)
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved, and currency to usd
        return {"book": book}

    # def get_success_url(self):
    #     return reverse_lazy(
    #         "accounting:create_asset_inventory_raw_material", kwargs={"pk": self.kwargs.get("pk")}
    #     )


# class RawGoodsReceipt(View):
#     template_name = "accounting/raw_goods_receipt.html"

#     def form_invalid(self, request, form, formset, error_message=None):
#         return render(
#             request,
#             self.template_name,
#             {
#                 "form": form,
#                 "formset": formset,
#                 "error_message": error_message
#                 or "There were errors in your submission.",
#             },
#         )

#     # *args is tuple
#     # **kwargs is dictionary
#     def get(self, request, *args, **kwargs):
#         # print("your user information is:", request.user.member)
#         book_pk = kwargs.get("pk")
#         book = Book.objects.get(pk=book_pk)
#         form = RawMaterialGoodsReceiptForm(book=book)
#         # formset = GoodsReceiptItemFormSet()
#         formset = RawGoodsReceiptItemFormSet(prefix="receiveditem_set")
#         return render(request, self.template_name, {"form": form, "formset": formset})

#     def post(self, request, *args, **kwargs):
#         # self is the instance of the view, handling the request.
#         # CBVs are just Python classes, and self lets you access all the class's methods and attributes (e.g., self.model, self.template_name, self.object etc).
#         # Without it, your method wouldn’t be able to store or reuse data across other methods of the same view.

#         # request is the HttpRequest object that contains metadata about the request, such as form data, user information, and more.
#         # for example, request.POST contains the data submitted in a POST request.
#         # request.FILES, request.user, request.method (Session data, cookies, headers, etc.)
#         # You literally can’t process form submissions without it.

#         book_pk = kwargs.get("pk")
#         book = Book.objects.get(pk=book_pk)
#         form = RawMaterialGoodsReceiptForm(request.POST, book=book)
#         formset = RawGoodsReceiptItemFormSet(request.POST, prefix="receiveditem_set")
#         if form.is_valid() and formset.is_valid():
#             try:
#                 with transaction.atomic():
#                     # tz the form and formset data
#                     # Save the raw goods receipt and items
#                     raw_goods_receipt = form.save(commit=False)
#                     raw_goods_receipt.book = book
#                     raw_goods_receipt.save()
#                     items = formset.save(commit=False)
#                     # asset_accounts_receivable = AssetAccountsReceivable(book=book,)
#                     for item in items:
#                         item.goods_receipt = raw_goods_receipt
#                         item.raw_material.unit_cost = item.unit_cost
#                         item.raw_material.save(update_fields=["unit_cost"])
#                         item.save()
#                     payment_status = form.cleaned_data.get("payment_status")
#                     receipt_total_cost = raw_goods_receipt.total_cost()
#                     if payment_status:
#                         # If the payment status is paid, update the cash account
#                         cash_account = form.cleaned_data.get("cash_account")
#                         # cash_account = CashAccount.objects.get(cash_account)
#                         new_cash_account_balance = (
#                             cash_account.balance - receipt_total_cost
#                         )
#                         cash_account.balance = new_cash_account_balance
#                         cash_account.save(update_fields=["balance"])
#                         CashTransactionEntry_object = (
#                             CashTransactionEntry.objects.create(
#                                 book=book,
#                                 value=receipt_total_cost,
#                                 is_amount_positive=False,
#                                 type="purchase",
#                                 account=cash_account,
#                                 account_balance=cash_account.balance,
#                             )
#                         )
#                         CashTransactionEntry_object.save()
#                     else:

#                         liability_accounts_payable = LiabilityAccountsPayable.objects.create(
#                             supplier=raw_goods_receipt.supplier,
#                             book=book,
#                             amount=receipt_total_cost,
#                             is_amount_positive=False,
#                             raw_goods_receipt=raw_goods_receipt,
#                             # invoice
#                             # currency=raw_goods_receipt.currency,
#                         )
#                         liability_accounts_payable.save()

#                     return render(
#                         request,
#                         self.template_name,
#                         {
#                             "form": form,
#                             "formset": formset,
#                             "message": "Receipt created successfully!",
#                         },
#                     )
#             except Exception as e:
#                 form.add_error(None, f"An unexpected error occurred: {e}")
#                 return self.form_invalid(
#                     request,
#                     form,
#                     formset,
#                     error_message="An unexpected error occurred while processing your request.",
#                 )

#         # If invalid, print errors for debugging
#         print("Form errors:", form.errors)
#         print("Formset errors:", formset.errors)
#         return self.form_invalid(request, form, formset)


class FinishedGoodsReceipt(View):
    template_name = "accounting/finished_goods_receipt.html"

    def form_invalid(self, request, form, formset, error_message=None):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "error_message": error_message
                or "There were errors in your submission.",
            },
        )

    def get(self, request, *args, **kwargs):
        book_pk = kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        form = FinishedGoodsReceiptForm(book=book)
        # formset = GoodsReceiptItemFormSet()
        formset = FinishedGoodsReceiptItemFormSet(prefix="receiveditem_set")
        return render(request, self.template_name, {"form": form, "formset": formset})

    def post(self, request, *args, **kwargs):
        book_pk = kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        form = FinishedGoodsReceiptForm(request.POST, book=book)
        formset = FinishedGoodsReceiptItemFormSet(
            request.POST, prefix="receiveditem_set"
        )
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Process the form and formset data
                    # Save the raw goods receipt and items
                    finished_goods_receipt = form.save(commit=False)
                    finished_goods_receipt.book = book
                    finished_goods_receipt.save()
                    items = formset.save(commit=False)
                    for item in items:
                        item.goods_receipt = finished_goods_receipt
                        item.finished_good.unit_cost = item.unit_cost
                        item.finished_good.save(update_fields=["unit_cost"])
                        item.save()

                    payment_status = form.cleaned_data.get("payment_status")
                    receipt_total_cost = finished_goods_receipt.total_cost
                    if payment_status:
                        # If the payment status is paid, update the cash account
                        cash_account = form.cleaned_data.get("cash_account")
                        # cash_account = CashAccount.objects.get(pk=cash_account.pk)

                        new_cash_account_balance = (
                            cash_account.balance - receipt_total_cost
                        )
                        cash_account.balance = new_cash_account_balance
                        cash_account.save(update_fields=["balance"])
                        CashTransactionEntry_object = (
                            CashTransactionEntry.objects.create(
                                book=book,
                                value=receipt_total_cost,
                                is_amount_positive=False,
                                type="purchase",
                                account=cash_account,
                                account_balance=cash_account.balance,
                            )
                        )
                        CashTransactionEntry_object.save()
                    else:
                        liability_accounts_payable = LiabilityAccountsPayable.objects.create(
                            supplier=finished_goods_receipt.supplier,
                            book=book,
                            amount=receipt_total_cost,
                            is_amount_positive=False,
                            finished_goods_receipt=finished_goods_receipt,
                            # invoice
                            # currency=raw_goods_receipt.currency,
                        )
                        liability_accounts_payable.save()
                    return render(
                        request,
                        self.template_name,
                        {
                            "form": form,
                            "formset": formset,
                            "message": "Receipt created successfully!",
                        },
                    )
            except Exception as e:
                form.add_error(None, f"An unexpected error occurred: {e}")
                return self.form_invalid(form)

        # If invalid, print errors for debugging
        print("Form errors:", form.errors)
        print("Formset errors:", formset.errors)
        return self.form_invalid(request, form, formset)


# # api calls
# def asset_inventory_raw_material_lookup(request, pk):
#     book = get_object_or_404(Book, pk=pk)
#     if request.method == "GET":
#         query = request.GET.get("{{ form.prefix }}-raw_material_name", "")
#         if query:
#             # raw_materials = AssetInventoryRawMaterial.objects.filter(name__icontains=query)
#             matches = AssetInventoryRawMaterial.objects.filter(
#                 name__icontains=query, book=book
#             ).values_list("name", flat=True)[:5]
#         else:
#             matches = AssetInventoryRawMaterial.objects.none()
#         # data = [{"id": match.pk, "name": match.name} for match in matches]
#         return render(
#             request,
#             "partials/material_suggestions.html",
#             {"materials": matches, "query": query},
#         )
#     return HttpResponse("<p class='error'>Invalid request method</p>", status=400)


# create pay accounts payable
# add transaction
# deduct from cash account.


class PayLiabilityAccountsPayable(generic.edit.FormView):
    # book = self.kwargs.get()
    # model = LiabilityAccountsPayable
    form_class = PayLiabilityAccountsPayableForm
    template_name = "accounting/pay_liability_accounts_payable.html"

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below pre-selecting the book field in the form according to the pk in the url
    # get initial is a function that is applicable to update and create views like these forms.
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        # By default make the currency US Dollars (which is 1)
        return {"book": book}

    def form_valid(self, form):
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        with transaction.atomic():
            try:
                liability_accounts_payable = form.cleaned_data[
                    "liability_accounts_payable"
                ]
                cash_account = form.cleaned_data["cash_account"]
            except KeyError as e:
                raise ValidationError({str(e): "This field is required."})
            except LiabilityAccountsPayable.DoesNotExist:
                raise ValidationError(
                    {"liability_accounts_payable": "Liability record not found."}
                )
            except CashAccount.DoesNotExist:
                raise ValidationError({"cash_account": "Cash account not found."})

            liability_accounts_payable.paid = True
            liability_accounts_payable.paid_with_cash_account = cash_account
            cash_account.balance -= liability_accounts_payable.amount
            liability_accounts_payable.save(
                update_fields=["paid", "paid_with_cash_account"]
            )
            cash_account.save(update_fields=["balance"])

            # later add cash_transaction_entry

            handle_payable_and_receivable(
                book=book,
                amount=liability_accounts_payable.amount,
                currency=cash_account.currency,
                model_instance=liability_accounts_payable,
                model_pk=liability_accounts_payable.pk,
                cash_account=cash_account,
            )

            # continue logic...
            return super().form_valid(form)

    # Takes you to the newly created book's detail page
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:index")


# create get accounts receivable
# add transaction
# add to cash account.


class GetAssetAccountsReceivable(generic.edit.FormView):
    # book = self.kwargs.get()
    # model = LiabilityAccountsPayable
    form_class = GetAssetAccountsReceivableForm
    template_name = "accounting/get_asset_accounts_receivable.html"

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    # below pre-selecting the book field in the form according to the pk in the url
    # get initial is a function that is applicable to update and create views like these forms.
    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        # By default make the currency US Dollars (which is 1)
        return {"book": book}

    def form_valid(self, form):
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        with transaction.atomic():
            try:
                asset_accounts_receivable = form.cleaned_data[
                    "asset_accounts_receivable"
                ]
                cash_account = form.cleaned_data["cash_account"]
            except KeyError as e:
                raise ValidationError({str(e): "This field is required."})
            except LiabilityAccountsPayable.DoesNotExist:
                raise ValidationError(
                    {"asset_accounts_receivable": "Liability record not found."}
                )
            except CashAccount.DoesNotExist:
                raise ValidationError({"cash_account": "Cash account not found."})

            asset_accounts_receivable.paid = True
            asset_accounts_receivable.paid_to_cash_account = cash_account
            cash_account.balance += asset_accounts_receivable.amount
            asset_accounts_receivable.save(
                update_fields=["paid", "paid_to_cash_account"]
            )
            cash_account.save(update_fields=["balance"])

            # later add cash_transaction_entry

            handle_payable_and_receivable(
                book=book,
                amount=asset_accounts_receivable.amount,
                currency=cash_account.currency,
                model_instance=asset_accounts_receivable,
                model_pk=asset_accounts_receivable.pk,
                cash_account=cash_account,
            )

            # continue logic...
            return super().form_valid(form)

    # Takes you to the newly created book's detail page
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:index")


# def kpi_dashboard(request, pk):
#     # gets it from urls.py
#     book = Book.objects.get(pk=pk)
#     today = timezone.now().date()
#     start_of_month = today.replace(day=1)

#     # Total balance (all cash accounts)
#     # balance = CashAccount.objects.filter(book=book).aggregate(
#     #     total_balance=Sum("balance")
#     # )["total_balance"] or Decimal("0.00")
#     balance = get_total_base_currency_balance(book_pk=pk)

#     # Transactions for this book between start of month and today
#     transactions = CashTransactionEntry.objects.filter(
#         book=book,
#         created_at__date__gte=start_of_month,
#         created_at__date__lte=today
#     )

#     money_in = sum(t.amount for t in transactions if t.is_amount_positive)
#     money_out = sum(t.amount for t in transactions if not t.is_amount_positive)

#     # Money in and out (all transactions)
#     # money_in = CashTransactionEntry.objects.filter(
#     #     book=book, is_amount_positive=True
#     # ).aggregate(total_in=Sum("amount"))["total_in"] or Decimal("0.00")

#     # money_out = CashTransactionEntry.objects.filter(
#     #     book=book, is_amount_positive=False
#     # ).aggregate(total_out=Sum("amount"))["total_out"] or Decimal("0.00")

#     # Burn = Money Out - Money In (or just Money Out if you prefer)

#     burn = money_out - money_in
#     avg_burn = 5000 #usd per month
#     # Runway = balance / burn (months), avoid division by zero
#     runway = (
#         (balance / avg_burn ).quantize(Decimal("0.1")) if avg_burn > 0 else None
#     )

#     # Growth rate (optional, example: (balance + money_in) / balance)
#     growth_rate = (
#         ((balance + money_in) / balance * 100 - 100).quantize(Decimal("0.1"))
#         if balance > 0
#         else None
#     )

#     # Default alive = True if balance > 0
#     default_alive = balance > 0

#     context = {
#         "balance": balance,
#         "money_in": money_in,
#         "money_out": money_out,
#         "burn": burn,
#         "runway": runway,
#         "growth_rate": growth_rate,
#         "default_alive": default_alive,
#     }

#     return render(request, "accounting/kpi_dashboard.html", context)


# ============================================================================
# SALES DASHBOARD VIEW - Modern order listing with profit calculation
# ============================================================================
from operating.models import Order, OrderItem
from django.core.paginator import Paginator


@method_decorator(login_required, name="dispatch")
class SalesDashboardView(View):
    """Modern sales dashboard showing orders with revenue, cost, and profit."""
    
    template_name = "accounting/sales_dashboard.html"
    
    def get(self, request):
        # Get filter parameters
        days_filter = request.GET.get('days', '365')  # Default to 1 year
        search_query = request.GET.get('search', '').strip()
        page = request.GET.get('page', 1)
        
        # Calculate date range
        try:
            days = int(days_filter)
        except ValueError:
            days = 365
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Base queryset - orders with original_price (web orders)
        orders = Order.objects.filter(
            created_at__gte=start_date,
            original_price__isnull=False
        ).exclude(
            payment_status='failed'
        ).select_related('web_client').prefetch_related(
            'items__product', 'items__product_variant'
        ).order_by('-created_at')
        
        # Search filter by customer name
        if search_query:
            orders = orders.filter(
                Q(web_client__name__icontains=search_query) |
                Q(web_client__username__icontains=search_query) |
                Q(guest_first_name__icontains=search_query) |
                Q(guest_last_name__icontains=search_query) |
                Q(order_number__icontains=search_query)
            )
        
        # Calculate totals and build order list with profit
        total_revenue = Decimal('0')
        total_cost = Decimal('0')
        order_list = []
        
        for order in orders:
            # Get customer name
            if order.web_client:
                customer_name = order.web_client.name or order.web_client.username or "Unknown"
            elif order.guest_first_name or order.guest_last_name:
                customer_name = f"{order.guest_first_name or ''} {order.guest_last_name or ''}".strip()
            else:
                customer_name = "Unknown Customer"
            
            # Calculate order revenue, cost, and profit from items
            order_revenue = Decimal('0')
            order_profit = Decimal('0')
            
            for item in order.items.all():
                qty = item.quantity or Decimal('1')
                item_revenue = item.price * qty
                order_revenue += item_revenue
                
                # Calculate profit based on item type
                item_profit = Decimal('0')
                
                # Get variant cost and price
                variant_cost = Decimal('0')
                variant_price = Decimal('0')
                
                if item.product_variant:
                    variant_cost = item.product_variant.variant_cost or Decimal('0')
                    variant_price = item.product_variant.variant_price or Decimal('0')
                elif item.product:
                    variant_cost = item.product.cost or Decimal('0')
                    variant_price = item.product.price or Decimal('0')
                
                if item.is_custom_curtain:
                    # Custom Curtain Formula:
                    # Profit = Total Price - (Fabric Amount × (variant_cost + 1)) - (Total Price × 0.145)
                    # Where:
                    #   - Total Price = item.price × quantity
                    #   - Fabric Amount = custom_fabric_used_meters
                    #   - variant_cost + 1 = fabric cost + labor/overhead per meter
                    #   - 0.145 = 14.5% commission (payment processor/marketplace fee)
                    fabric_amount = item.custom_fabric_used_meters or Decimal('0')
                    fabric_cost_with_labor = fabric_amount * (variant_cost + Decimal('1'))
                    commission = item_revenue * Decimal('0.145')
                    item_profit = item_revenue - fabric_cost_with_labor - commission
                else:
                    # Standard Item: Profit = Quantity * (Sold Price - Cost)
                    # Sold Price is item.price
                    unit_margin = item.price - variant_cost
                    item_profit = qty * unit_margin
                
                order_profit += item_profit
            
            # Derive cost from Revenue and Profit to ensure consistency (Revenue - Cost = Profit)
            # Cost = Revenue - Profit
            order_cost = order_revenue - order_profit
            
            total_revenue += order_revenue
            total_cost += order_cost
            
            order_list.append({
                'id': order.id,
                'order_number': order.order_number or f"ORD-{order.id}",
                'customer_name': customer_name or "Unknown",
                'date': order.created_at,
                'revenue': order_revenue,
                'cost': order_cost,
                'profit': order_profit,
                'status': order.order_status or order.payment_status or 'pending',
                'payment_status': order.payment_status,
            })
        
        total_profit = total_revenue - total_cost
        order_count = len(order_list)
        
        # Paginate
        paginator = Paginator(order_list, 20)  # 20 per page
        page_obj = paginator.get_page(page)
        
        # Period stats
        week_ago = end_date - timedelta(days=7)
        month_ago = end_date - timedelta(days=30)
        
        week_revenue = sum(
            o['revenue'] for o in order_list 
            if o['date'] >= week_ago
        )
        month_revenue = sum(
            o['revenue'] for o in order_list 
            if o['date'] >= month_ago
        )
        
        context = {
            'orders': page_obj,
            'page_obj': page_obj,
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'order_count': order_count,
            'week_revenue': week_revenue,
            'month_revenue': month_revenue,
            'year_revenue': total_revenue,
            'days_filter': days_filter,
            'search_query': search_query,
        }
        
        # Return partial template for HTMX requests
        if request.headers.get('HX-Request'):
            return render(request, 'accounting/partials/sales_content.html', context)
        
        return render(request, self.template_name, context)
