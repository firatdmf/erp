from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse

# from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.views import View, generic

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
import yfinance as yf
from decimal import Decimal
import math
import time
from django.core.exceptions import ObjectDoesNotExist


def get_exchange_rate(self, from_currency, to_currency):
    ticker = f"{from_currency}{to_currency}=X"
    data = yf.Ticker(ticker)
    exchange_rate = data.history(period="1d")["Close"][0]
    return Decimal(exchange_rate)


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
    context_object_name = "Book"

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

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     book_pk = self.kwargs.get('pk')
    #     book = Book.objects.get(pk=book_pk)
    #     print(book)
    #     kwargs['book'] = [book_pk]
    #     return kwargs

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
        # Set the initial value of the book field to the book retrieved
        # below basically sets self.kwargs['book'] to the book object we retrieved
        return {"book": book}

    # You do this because you want to manually do some process before saving the Equity Capital when the capital form is submitted.
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            # 1 Add the transaction
            # 2 add the cash to AssetCash
            # 3 update balance on CashAccount
            # 4 update stakeholder total shares
            # 5 add EquityCapital

            # Setting up the variables from the form input
            book_pk = self.kwargs.get("pk")
            book = Book.objects.get(pk=book_pk)
            transaction_value = form.cleaned_data.get("amount")
            # transaction_currency = form.cleaned_data.get("currency")
            deposited_cash_account = form.cleaned_data.get("cash_account")
            deposited_cash_account = get_object_or_404(
                CashAccount, pk=deposited_cash_account.pk
            )
            currency = deposited_cash_account.currency

            new_deposited_cash_account_balance = (
                deposited_cash_account.balance + transaction_value
            )

            member = form.cleaned_data.get("member")
            member = Member.objects.get(pk=member.pk)
            new_shares_issued = form.cleaned_data.get("new_shares_issued")
            stakeholderbook = StakeholderBook.objects.get(member=member, book=book)

            # 1 adding the transaction transaction
            # there could be possible errors here in the future.
            transaction_type = "capital"
            try:
                latest_equity_capital_item = EquityCapital.objects.filter(
                    book=book
                ).latest("created_at")
                type_pk = latest_equity_capital_item.pk + 1
            except self.model.DoesNotExist:
                type_pk = 1

            # 1 Creating the new transaction entry into the database
            transaction = Transaction.objects.create(
                book=book,
                value=transaction_value,
                currency=currency,
                type=transaction_type,
                type_pk=type_pk,
                account=deposited_cash_account,
                account_balance=new_deposited_cash_account_balance,
            )

            # ---------------------------------------------------------------
            # 2 adding the cash to AssetCash
            # Get the current balance inside the cash account
            try:
                asset_cash = AssetCash.objects.filter(
                    book=book, currency=currency
                ).latest("created_at")
                asset_cash_balance = asset_cash.currency_balance
            except ObjectDoesNotExist:
                asset_cash_balance = 0

            asset_cash_balance += transaction_value

            new_asset_cash = AssetCash.objects.create(
                book=book,
                currency=currency,
                amount=transaction_value,
                transaction=transaction,
                currency_balance=asset_cash_balance,
            )
            # ---------------------------------------------------------------
            # 3 now updating cash balance on cash account

            # get the current balance and add the transaction value to it
            deposited_cash_account.balance = new_deposited_cash_account_balance
            deposited_cash_account.save()

            # new_asset = Asset.objects.create(book = self.kwargs.get('pk'), )

            # ---------------------------------------------------------------
            # 4 update stakeholder total shares
            stakeholderbook.shares += new_shares_issued
            stakeholderbook.save()
            # ---------------------------------------------------------------
            # 5 save the form
            # create the form object but do not save yet
            my_form = form.save(commit=False)
            # submit the capital form currency input the same as the selected deposit account's currency
            my_form.currency = currency
            my_form.save()

            # This method saves the form instance to the database and then redirects the user to a success URL.
            return self.form_valid(form)
        else:
            for field in form:
                print("Field Error:", field.name, field.errors)

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:add_equity_capital", kwargs={"pk": self.kwargs.get("pk")}
        )


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

    # You do this because you want to manually do some process when the expense form is submitted.
    def post(self, request, *args, **kwargs):
        start_time = time.time()

        # return(HttpResponse("now get outta here!"))
        # just kidding

        # let's get the form values first
        form = self.get_form()

        if form.is_valid():
            # Here is what we will do here
            # 1 Create a Transaction model entry
            # 2 Create a AssetCash model entry
            # 3 Update the CashAccount balance
            # 4 Create a EquityRevenue model entry

            # Get the book id number from the kwargs
            book_pk = self.kwargs.get("pk")
            book = Book.objects.get(pk=book_pk)
            # We need to find the of the last revenue item, because we need to know the pk of the next revenue item so we can put into transaction model entry as a reference

            # Get the next pk in the EquityRevenue
            try:
                latest_revenue_item = EquityRevenue.objects.filter(book=book).latest(
                    "pk"
                )
                type_pk = latest_revenue_item.pk + 1
            except ObjectDoesNotExist:
                type_pk = 1

            revenue_amount = form.cleaned_data.get("amount")

            # Get the selected cash account from the form
            deposited_cash_account = form.cleaned_data.get("cash_account")
            deposited_cash_account = CashAccount.objects.get(
                pk=deposited_cash_account.pk
            )
            new_deposited_cash_account_balance = (
                deposited_cash_account.balance + revenue_amount
            )

            # Set the currency to the deposited_cash_account's currency
            currency = deposited_cash_account.currency
            transaction_type = "revenue"
            # 1 Creating the transaction entry
            # You need error handling here.
            transaction = Transaction(
                book=book,
                value=form.cleaned_data.get("amount"),
                currency=currency,
                type=transaction_type,
                type_pk=type_pk,
                account=deposited_cash_account,
                account_balance=new_deposited_cash_account_balance,
            )
            transaction.save()

            # 2 Add AssetCash object

            new_asset_cash = AssetCash.objects.create(
                book=book,
                currency=currency,
                amount=revenue_amount,
                transaction=transaction,
                currency_balance=new_deposited_cash_account_balance,
            )

            # 3
            # Save the updated cash account
            deposited_cash_account.balance = new_deposited_cash_account_balance
            deposited_cash_account.save()

            # 4 Saving the Equity Revenue entry
            # Now you need to update the form instance before saving it
            # Create the model instance but don't save it yet
            my_form = form.save(commit=False)
            # my_form.account_balance = target_cash_account.balance
            # I handle this manually because I want to set the currency of the submitted revenue to be the same as the sent account's currency
            my_form.currency = currency
            my_form.save()
            return self.form_valid(form)
        else:
            for field in form:
                print("Field Error:", field.name, field.errors)

    # This is probably redundant but it's ok to keep it
    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:add_equity_revenue", kwargs={"pk": self.kwargs.get("pk")}
        )


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

    # You do this because you want to manually do some process when the expense form is submitted.
    def post(self, request, *args, **kwargs):
        # get the form object after the user hits submit
        form = self.get_form()
        # validate the form
        print("helo my friend")
        if form.is_valid():
            # 1 Add Transaction
            # 2 Add CashAsset
            # 3 Update CashAccount
            # 4 Add EquityExpense

            book_pk = self.kwargs.get("pk")
            book = Book.objects.get(pk=book_pk)

            expense_amount = form.cleaned_data.get("amount")
            withdrawn_cash_account = form.cleaned_data.get("cash_account")
            withdrawn_cash_account = CashAccount.objects.get(
                pk=withdrawn_cash_account.pk
            )
            new_withdrawn_cash_account_balance = (
                withdrawn_cash_account.balance - expense_amount
            )
            currency = withdrawn_cash_account.currency
            # print('withdrawn cash account currency is:', currency)
            # return JsonResponse(currency, safe=False)
            # return(HttpResponse(f"<p>withdrawn cash account currency is:, {currency}</p>"))

            # 1 Add the transaction
            # We are going to need this to find the next expense item's pk, and save in transaction entry
            try:
                latest_equity_expense_item = EquityExpense.objects.filter(
                    book=book
                ).latest("pk")
                type_pk = latest_equity_expense_item.pk + 1
            except ObjectDoesNotExist:
                type_pk = 1

            transaction_type = "expense"

            transaction = Transaction(
                book=book,
                value=expense_amount,
                currency=currency,
                type=transaction_type,
                account=withdrawn_cash_account,
                type_pk=type_pk,
                account_balance=new_withdrawn_cash_account_balance,
            )
            transaction.save()

            # 2 Add AssetCash object
            try:
                latest_asset_cash_object = AssetCash.objects.filter(
                    book=book, currency=currency
                ).latest("pk")
                currency_balance = latest_asset_cash_object.currency_balance
                # currency_balance += expense_amount
            except ObjectDoesNotExist:
                currency_balance = 0

            currency_balance -= expense_amount
            new_asset_cash = AssetCash.objects.create(
                book=book,
                currency=currency,
                amount=expense_amount,
                transaction=transaction,
                currency_balance=currency_balance,
            )

            # 3 Update the cash account object
            withdrawn_cash_account.balance = new_withdrawn_cash_account_balance
            withdrawn_cash_account.save()

            # 4  Save the Equity Expense object
            # Now you need to update the form instance before saving it
            # Create the model instance but don't save it yet
            my_form = form.save(commit=False)
            my_form.currency = currency
            my_form.save()
            return self.form_valid(form)
        else:
            return HttpResponse(
                "<h1>An error occured in the server. Please email howdy@nejum.com for technical support.</h1>"
            )
        return self.form_invalid(form)

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:add_equity_expense", kwargs={"pk": self.kwargs.get("pk")}
        )


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

    # You do this because you want to manually do some process when the expense form is submitted.
    def post(self, request, *args, **kwargs):

        form = self.get_form()
        if form.is_valid():
            # 1 Add Transaction
            # 2 Add CashAsset
            # 3 Update CashAccount
            # 4 Add EquityExpense

            book_pk = self.kwargs.get("pk")
            book = Book.objects.get(pk=book_pk)

            # Set up the variables from the form
            withdrawn_cash_account = form.cleaned_data.get("cash_account")
            withdrawn_cash_account = CashAccount.objects.get(
                pk=withdrawn_cash_account.pk
            )
            divident_amount = form.cleaned_data.get("amount")
            member = form.cleaned_data.get("member")
            member = Member.objects.get(pk=member.pk)
            new_withdrawn_cash_account_balance = (
                withdrawn_cash_account.balance - divident_amount
            )
            currency = withdrawn_cash_account.currency

            # 1 Add Transaction

            # Getting the next EquityDivident object's pk
            try:
                latest_equity_expense_item = EquityDivident.objects.filter(
                    book=book
                ).latest("pk")
                type_pk = latest_equity_expense_item.pk + 1
            except ObjectDoesNotExist:
                type_pk = 1

            transaction_type = "divident"

            transaction = Transaction(
                book=book,
                value=divident_amount,
                currency=currency,
                type=transaction_type,
                account=withdrawn_cash_account,
                type_pk=type_pk,
                account_balance=new_withdrawn_cash_account_balance,
            )
            transaction.save()

            # 2 Substract CashAsset
            try:
                latest_asset_cash_object = AssetCash.objects.filter(
                    book=book, currency=currency
                ).latest("pk")
                currency_balance = latest_asset_cash_object.currency_balance
                # currency_balance += expense_amount
            except ObjectDoesNotExist:
                currency_balance = 0

            currency_balance -= divident_amount
            new_asset_cash = AssetCash.objects.create(
                book=book,
                currency=currency,
                amount=divident_amount,
                transaction=transaction,
                currency_balance=currency_balance,
            )

            # 3 Update the balance of the cash account
            # Save the updated cash account
            withdrawn_cash_account.balance = new_withdrawn_cash_account_balance
            withdrawn_cash_account.save()

            # Now you need to update the form instance before saving it
            # Create the model instance but don't save it yet
            my_form = form.save(commit=False)
            my_form.currency = currency
            my_form.save()
            return self.form_valid(form)

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:add_equity_divident", kwargs={"pk": self.kwargs.get("pk")}
        )


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
class TransactionList(generic.ListView):
    model = Transaction
    template_name = "accounting/transaction_list.html"

    def get_queryset(self):
        book_pk = self.kwargs.get("pk")
        return Transaction.objects.filter(book=book_pk)
        # return Transaction.objects.filter(book=book_pk).select_related('book', 'account').prefetch_related('related_model_name')
        # return super().get_queryset()


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
class MakeInTransfer(generic.edit.FormView):
    form_class = InTransferForm
    template_name = "accounting/make_in_transfer.html"

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounting:make_in_transfer", kwargs={"pk": self.kwargs.get("pk")}
        )

    # below gets the book value from the url and puts it into keyword arguments (it is important because in the forms.py file we use it to filter possible cash accounts for that book)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        book_pk = self.kwargs.get("pk")
        book = Book.objects.get(pk=book_pk)
        kwargs["book"] = book
        return kwargs

    def form_valid(self, form):
        # Process the form data
        amount = form.cleaned_data["amount"]
        date = form.cleaned_data["date"]
        from_cash_account = form.cleaned_data["from_cash_account"]
        from_cash_account = CashAccount.objects.get(pk=from_cash_account.pk)
        from_cash_account_new_balance = from_cash_account.balance - amount
        from_cash_account.balance = from_cash_account_new_balance
        from_cash_account.save()

        transaction1 = Transaction(
            book=from_cash_account.book,
            value=amount,
            currency=from_cash_account.currency,
            type="transfer",
            account=from_cash_account,
            type_pk=None,
            account_balance=from_cash_account_new_balance,
        )
        transaction1.save()
        print(f"from cash account is: {from_cash_account}")
        to_cash_account = form.cleaned_data["to_cash_account"]
        to_cash_account = CashAccount.objects.get(pk=to_cash_account.pk)
        to_cash_account_new_balance = to_cash_account.balance + amount
        to_cash_account.balance = to_cash_account_new_balance
        to_cash_account.save()

        transaction2 = Transaction(
            book=to_cash_account.book,
            value=amount,
            currency=to_cash_account.currency,
            type="transfer",
            account=to_cash_account,
            type_pk=None,
            account_balance=to_cash_account_new_balance,
        )
        transaction2.save()
        # Add your processing logic here
        return super().form_valid(form)


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

    def form_valid(self, form):
        # Process the form data
        from_amount = form.cleaned_data["from_amount"]
        to_amount = form.cleaned_data["to_amount"]
        # currency_rate = form.cleaned_data["currency_rate"]
        # converted_amount = currency_rate * amount
        date = form.cleaned_data["date"]
        from_cash_account = form.cleaned_data["from_cash_account"]
        from_cash_account = CashAccount.objects.get(pk=from_cash_account.pk)
        from_cash_account_new_balance = from_cash_account.balance - from_amount
        from_cash_account.balance = from_cash_account_new_balance
        from_cash_account.save()

        transaction1 = Transaction(
            book=from_cash_account.book,
            value=from_amount,
            currency=from_cash_account.currency,
            type="exchange",
            account=from_cash_account,
            type_pk=None,
            account_balance=from_cash_account_new_balance,
        )
        transaction1.save()
        print(f"from cash account is: {from_cash_account}")
        to_cash_account = form.cleaned_data["to_cash_account"]
        to_cash_account = CashAccount.objects.get(pk=to_cash_account.pk)
        to_cash_account_new_balance = to_cash_account.balance + to_amount
        to_cash_account.balance = to_cash_account_new_balance
        to_cash_account.save()

        transaction2 = Transaction(
            book=to_cash_account.book,
            value=to_amount,
            currency=to_cash_account.currency,
            type="exchange",
            account=to_cash_account,
            type_pk=None,
            account_balance=to_cash_account_new_balance,
        )
        transaction2.save()
        # Add your processing logic here
        return super().form_valid(form)


# below are added after august 4, 2025 and for the new cogs system

# accounting.py (or similar location)


class CreateAssetInventoryRawMaterial(generic.CreateView):
    model = AssetInventoryRawMaterial
    form_class = AssetInventoryRawMaterialForm
    template_name = "accounting/create_asset_inventory_raw_material.html"
    success_url = reverse_lazy(
        "accounting:create_asset_inventory_raw_material", kwargs={"pk": "pk"}
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


class GoodsReceipt(View):
    template_name = "accounting/goods_receipt.html"

    def get(self, request, *args, **kwargs):
        form = GoodsReceiptForm()
        # formset = GoodsReceiptItemFormSet()
        formset = GoodsReceiptItemFormSet(prefix="receiveditem_set")
        return render(request, self.template_name, {"form": form, "formset": formset})
