# Generated by Django 4.2.4 on 2025-02-10 11:07

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0054_assetcash_amount_equitycapital_currency_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='equitycapital',
            name='shares_issued',
            field=models.PositiveSmallIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='equitycapital',
            name='note',
            field=models.TextField(default='tsdsa'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='due_date',
            field=models.DateField(default=datetime.datetime(2025, 3, 12, 11, 7, 5, 236697, tzinfo=datetime.timezone.utc)),
        ),
    ]
