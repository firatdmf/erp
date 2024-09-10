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
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
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



# Cash, Land, Furniture, Accounts Receivable, Office Supplies
class Asset(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, blank=False, null=False)
    name = models.CharField(max_length=100)
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(
        CurrencyCategory,
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        default = 1
    )
    created_at = models.DateTimeField(auto_now_add=True)
    depreciating = models.BooleanField(default=False)
    residual_value = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True)
    useful_life_in_months = models.DecimalField(max_digits=10, decimal_places=0,blank=True,null=True)

    def __str__(self):
        return f"Book: {self.book.name}, Asset name: {self.name}"
    