# Generated by Django 4.2.4 on 2024-11-30 20:51

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0031_alter_invoice_due_date_alter_invoice_total_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='due_date',
            field=models.DateField(default=datetime.datetime(2024, 12, 30, 20, 51, 15, 330917, tzinfo=datetime.timezone.utc)),
        ),
    ]
