from django.db import models
from crm.models import Company, Contact
# Create your models here.

class Book(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    class Meta:
        verbose_name_plural = "Expense Categories"


def usd():
    return "usd"


class CurrencyCategory(models.Model):
    name = models.CharField(max_length=8, unique=True)

    def __str__(self):
        return self.name
    class Meta:
        verbose_name_plural = "Currency Categories"


class Expense(models.Model):
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.CASCADE, blank=True, null=True
    )
    currency = models.ForeignKey(
        CurrencyCategory, on_delete=models.CASCADE, blank=True, null=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=200, unique=False, blank=True)
    book = models.ForeignKey(Book,on_delete=models.CASCADE, blank=False,null=False)

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
        CurrencyCategory, on_delete=models.CASCADE, blank=True, null=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=200, unique=False, blank=True)
    book = models.ForeignKey(Book,on_delete=models.CASCADE, blank=False,null=False)


    def __str__(self):
        # return f"{self.category.name} - {self.amount}"
    
        try:
        # return f"{self.amount} {self.currency} - {self.date.strftime('%m/%d/%Y')} - {self.category.name}"
            return f"Book: {self.book} - {self.amount} {self.currency} - {self.date.strftime('%d %B, %Y')} - {self.category.name}"
        except AttributeError:
            return f"Book: {self.book} - {self.amount} {self.currency} - {self.date.strftime('%m/%d/%Y')}"
