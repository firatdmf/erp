# Generated by Django 4.2.4 on 2025-01-26 10:19

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0039_transaction_type_pk_alter_invoice_due_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='equityexpense',
            name='account_balance',
        ),
        migrations.AlterField(
            model_name='invoice',
            name='due_date',
            field=models.DateField(default=datetime.datetime(2025, 2, 25, 10, 19, 38, 320457, tzinfo=datetime.timezone.utc)),
        ),
    ]
