# Generated by Django 4.2.4 on 2025-01-24 20:38

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0035_alter_book_created_at_alter_invoice_due_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='due_date',
            field=models.DateField(default=datetime.datetime(2025, 2, 23, 20, 38, 30, 743729, tzinfo=datetime.timezone.utc)),
        ),
    ]
