from django.db import models
from crm.models import Contact, Company
from django.contrib.postgres.fields import ArrayField
# Create your models here.

class RawMaterialCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    unit = models.CharField(max_length=10, unique=False, default="piece")
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Raw Material Categories"
    

class RawMaterial(models.Model):
    name = models.CharField(max_length=50, unique=True)
    type = models.ForeignKey(RawMaterialCategory, on_delete=models.CASCADE, blank=False, null=False)
    supplierContact = models.ManyToManyField(
        Contact,
        blank=True,
    )

    supplierCompany = models.ManyToManyField(
        Company, 
        blank=True,
    )
    cost = models.DecimalField(max_digits=6, decimal_places=2)

class UnitCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    decimals = models.IntegerField()
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Unit Categories"

class Machine(models.Model):
    name = models.CharField(max_length=50, unique=True)
    max_rpm  = models.PositiveIntegerField()
    domain = models.DecimalField(max_digits=5, decimal_places=2)

class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, blank=False)
    name = models.CharField(max_length=50, unique=True, blank= True, null=True)
    description = models.CharField(max_length=250, blank= True, null=True)
    variant = ArrayField(ArrayField(models.CharField()), blank=True,null=True)
    # machine = models.ForeignKey(Machine, on_delete=models.CASCADE, blank=False,null=False)
    cost = models.DecimalField(max_digits=6, decimal_places=2,unique=False, blank=True)
    # unit = models.CharField(max_length=10, unique=False, default="piece")
    unit = models.ForeignKey(UnitCategory, on_delete=models.CASCADE, blank=False, null=False )
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=2,unique=False, blank=True)
    raw_materials = models.ManyToManyField(RawMaterial)
