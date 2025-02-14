from django.db import models

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



