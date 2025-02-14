from django.db import models
from crm.models import Contact, Company
from accounting.models import AssetInventoryRawMaterial
from django.contrib.postgres.fields import ArrayField


# Create your functions here.
def product_description():
    return {
        "variant": [
            {
                "id": 123,
                "price": 2,
                "quantity": 20,
            },
            {
                "id": 456,
                "price": 5,
                "quantity": 10,
            },
        ]
    }

# Create your models here.


class Machine(models.Model):
    name = models.CharField(max_length=150, unique=True)
    max_rpm = models.PositiveIntegerField()
    domain = models.DecimalField(max_digits=5, decimal_places=2)


class Product(models.Model):
    name = models.CharField(max_length=300, unique=True)
    sku = models.CharField(max_length=12, unique=True)
    # Probably you should not allow direct materials to be used here.
    ingredient = models.ManyToManyField(AssetInventoryRawMaterial, related_name='products')
    # variant = 
    # product_type = 


