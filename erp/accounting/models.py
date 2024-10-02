from django.db import models
from crm.models import Company, Contact
from operating.models import Product

# Create your models here.


class CurrencyCategory(models.Model):
    name = models.CharField(max_length=8, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Currency Categories"


class Book(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Stakeholder(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    books = models.ManyToManyField(Book,related_name="Books")
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=200, unique=False, blank=True, null=True)

    # A stakeholder's ownership percentage is calculated by: [#shares/(Capital Stock)]*100%
    # share = models.DecimalField(max_digits=10, decimal_places=2, blank=False, null=False, default=1) 

    def __str__(self):
        # Books are many to many field so we need to iterate and put them here
        book_names = ", ".join(book.name for book in self.books.all())
        # return f"{self.name}"
        return self.name


class Account(models.Model):
    name = models.CharField(max_length=50, unique=True)
    currency = models.ForeignKey(
        CurrencyCategory,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

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


class Expense(models.Model):
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.CASCADE, blank=True, null=True
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
    created_at = models.DateTimeField(auto_now_add=True)

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
    created_at = models.DateTimeField(auto_now_add=True)


class AssetCategory(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Asset Categories"

    def __str__(self):
        return self.name


class CashCategory(models.Model):
    class Meta:
        verbose_name_plural = "Cash Categories"
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    # name = models.CharField(max_length=100)
    name = models.CharField(max_length=6, blank=False, null=False, unique=True)
    # last_four_digits = models.DecimalField(max_digits=4, decimal_places=0,blank=True,null=True)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.book} | {self.name} | {self.currency} | balance: {self.balance}"
    


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
    depreciating = models.BooleanField(default=False)
    residual_value = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    useful_life_in_months = models.DecimalField(
        max_digits=10, decimal_places=0, blank=True, null=True
    )

    def __str__(self):
        return f"Book: {self.book.name}, Asset Category: {self.category}, Asset Name: {self.name}, Asset Value: {self.currency}{'{:20,.2f}'.format(self.value)}"


class Transaction(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    # 1 for addition, 0 for subtraction
    operation = models.BooleanField()
    value = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )


class Capital(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    # The name of the person or company who provides the capital
    provider = models.ForeignKey(Stakeholder, on_delete=models.CASCADE, blank=False, null=False)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )
    CashCategory = models.ForeignKey(
        CashCategory, on_delete=models.CASCADE, blank=False, null=False, default=1
    )

    
    

    def __str__(self):
        return f"{self.currency}{self.value} | {self.provider}"


