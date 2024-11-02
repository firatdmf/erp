from django.db import models
from crm.models import Company, Contact
from operating.models import Product
from django.utils import timezone

# Create your models here.


class CurrencyCategory(models.Model):
    code = models.CharField(max_length=3, unique=True)  # e.g., USD, EUR, TRY
    name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=5, blank=True, null=True)  # e.g., $, €, ₺

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name_plural = "Currency Categories"


# The books is to keep the separate entities apart for accounting, and operating purposes.
class Book(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class CashAccount(models.Model):
    class Meta:
        verbose_name_plural = "Cash Accounts"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    # name = models.CharField(max_length=100)
    name = models.CharField(max_length=12, blank=False, null=False, unique=True)
    # last_four_digits = models.DecimalField(max_digits=4, decimal_places=0,blank=True,null=True)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} | Balance: {self.currency.symbol}{self.balance} ({self.book})"


class Stakeholder(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=200, unique=False, blank=True, null=True)
    books = models.ManyToManyField(Book, related_name="stakeholders")

    # Currency for the contributions
    # currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE, default=1)  # Default currency

    # A stakeholder's ownership percentage is calculated by: [#shares/(Capital Stock)]*100%
    # 100 FOR 100%
    share = models.DecimalField(max_digits=5, decimal_places=2, blank=False, null=False, default=100)

    def __str__(self):
        # Books are many to many field so we need to iterate and put them here
        book_names = ", ".join(book.name for book in self.books.all())
        # return f"{self.name}"
        return self.name


# class Equity(models.Model):
#     class Meta:
#         verbose_name_plural = "Equities"
#     created_at = models.DateTimeField(auto_now_add=True)
#     book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
#     # The name of the person or company who provides the capital
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     description = models.CharField(max_length=200, blank=True, null=True)
#     # currency = models.ForeignKey(
#     #     CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
#     # )
#     # date_invested = models.DateField()

#     def __str__(self):
#         return f"{self.currency}{self.value} | {self.stakeholder}"


class EquityCapital(models.Model):
    class Meta:
        verbose_name_plural = "Equity Capitals"

    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    stakeholder = models.ForeignKey(
        Stakeholder, on_delete=models.CASCADE, blank=False, null=False
    )
    cash_account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, blank=False, null=False
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    note = models.CharField(max_length=200, blank=True, null=True)
    date_invested = models.DateField()

    def __str__(self):
        return (self.stakeholder.name + ' ' + self.cash_account.name + ' ' + self.cash_account.currency.symbol + str(self.amount) + ' ' + str(self.date_invested))
        # return (self.cash_account.currency.symbol + str(self.amount))


# class Account(models.Model):
#     name = models.CharField(max_length=50, unique=True)
#     currency = models.ForeignKey(
#         CurrencyCategory,
#         on_delete=models.CASCADE,
#         blank=True,
#         null=True,
#     )

#     def __str__(self):
#         return self.name


# Not used for now
class Source(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Expense Categories"


# def usd():
#     return "usd"


class EquityExpense(models.Model):
    class Meta:
        verbose_name_plural = "Equity Expenses"
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.CASCADE, blank=True, null=True
    )
    cash_account = models.ForeignKey(
        CashAccount, on_delete=models.CASCADE, blank=False, null=False
    )
    currency = models.ForeignKey(
        CurrencyCategory,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=200, unique=False, blank=True)

    def __str__(self):
        try:
            # return f"{self.amount} {self.currency} - {self.date.strftime('%m/%d/%Y')} - {self.category.name}"
            return f"Book: {self.book} - {self.amount} {self.currency} - {self.date.strftime('%d %B, %Y')} - {self.category.name}"
        except AttributeError:
            return f"Book: {self.book} - {self.amount} {self.currency} - {self.date.strftime('%m/%d/%Y')}"


class IncomeCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Income Categories"


class Income(models.Model):
    category = models.ForeignKey(
        IncomeCategory, on_delete=models.CASCADE, blank=True, null=True
    )
    currency = models.ForeignKey(
        CurrencyCategory,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=200, unique=False, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # return f"{self.category.name} - {self.amount}"

        try:
            # return f"{self.amount} {self.currency} - {self.date.strftime('%m/%d/%Y')} - {self.category.name}"
            return f"Book: {self.book} - {self.amount} {self.currency} - {self.date.strftime('%d %B, %Y')} - {self.category.name}"
        except AttributeError:
            return f"Book: {self.book} - {self.amount} {self.currency} - {self.date.strftime('%m/%d/%Y')}"


class Sale(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, blank=False, null=False
    )
    quantity = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True
    )


class AssetCategory(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Asset Categories"

    def __str__(self):
        return self.name


class Transaction(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, blank=False, null=False)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    type = models.CharField(max_length=50, blank=False, null=False, unique=True)
    description = models.CharField(max_length=200, blank=False, null=False, unique=True)
    # ID of source
    source = models.ForeignKey(
        Source, on_delete=models.CASCADE, blank=False, null=False
    )
    # ID of target
    # target = models.ForeignKey(Source, on_delete=models.CASCADE, blank=False, null=False)
    currency = models.ForeignKey(
        CurrencyCategory,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=False, null=False
    )
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )
    operation = models.BooleanField(blank=False, null=False)


# Equity: Capital + Rev - Exp - Dividends
# Cash, Land, Furniture, Accounts Receivable, Office Supplies
class Asset(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    name = models.CharField(max_length=100)
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )
    created_at = models.DateTimeField(auto_now_add=True)
    purchase_date = models.DateField()
    depreciating = models.BooleanField(default=False)
    residual_value = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    useful_life_in_months = models.DecimalField(
        max_digits=10, decimal_places=0, blank=True, null=True
    )

    def __str__(self):
        return f"Book: {self.book.name}, Asset Category: {self.category}, Asset Name: {self.name}, Asset Value: {self.currency}{'{:20,.2f}'.format(self.value)}"


class Liability(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True, null=True)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.ForeignKey(CurrencyCategory, on_delete=models.CASCADE)
    due_date = models.DateField()

    def __str__(self):
        return f"{self.name} - {self.value} {self.currency.code}"


# class Transaction(models.Model):
#     created_at = models.DateTimeField(auto_now_add=True)
#     book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
#     # 1 for addition, 0 for subtraction
#     operation = models.BooleanField()
#     value = models.DecimalField(max_digits=10, decimal_places=2)
#     currency = models.ForeignKey(
#         CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
#     )
