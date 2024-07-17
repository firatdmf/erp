from django.db import models
from crm.models import Company, Contact

# Create your models here.


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Expense(models.Model):
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.CASCADE, blank=True, null=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=200, unique=False, blank=True)

    def __str__(self):
        try:
            return f"{self.category.name} - {self.amount} - {self.date}"
        except(AttributeError):
            return f"- {self.amount} - {self.date}"



class IncomeCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Income(models.Model):
    category = models.ForeignKey(IncomeCategory, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=200, unique=False, blank=True)

    def __str__(self):
        return f"{self.category.name} - {self.amount}"
