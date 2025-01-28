# Generated by Django 4.2.4 on 2025-01-26 09:32

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0038_transaction_account_alter_invoice_due_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='type_pk',
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='due_date',
            field=models.DateField(default=datetime.datetime(2025, 2, 25, 9, 32, 54, 874459, tzinfo=datetime.timezone.utc)),
        ),
    ]
