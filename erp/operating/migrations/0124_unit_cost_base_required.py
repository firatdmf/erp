# Every stock item carries what it cost (8426375d). All rows on prod had a
# cost when this was written (9,453 on 2026-11-17), so this only sets NOT NULL.

from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0123_shippingrule_retired'),
    ]

    operations = [
        migrations.AlterField(
            model_name='warehouseproductitem',
            name='unit_cost_base',
            field=models.DecimalField(decimal_places=4, help_text="Unit cost when received, in the owning book's base currency", max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal('0'))]),
        ),
    ]
