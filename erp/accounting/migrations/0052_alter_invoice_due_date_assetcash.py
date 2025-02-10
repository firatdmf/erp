# Generated by Django 4.2.4 on 2025-02-10 09:48

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0051_alter_cashaccount_name_alter_invoice_due_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='due_date',
            field=models.DateField(default=datetime.datetime(2025, 3, 12, 9, 48, 52, 194226, tzinfo=datetime.timezone.utc)),
        ),
        migrations.CreateModel(
            name='AssetCash',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('balance', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounting.book')),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounting.currencycategory')),
                ('transaction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounting.transaction')),
            ],
        ),
    ]
