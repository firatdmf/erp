# Generated by Django 4.2.4 on 2024-11-23 13:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0022_alter_equityrevenue_invoice_number'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquityDivident',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date', models.DateField()),
                ('description', models.CharField(blank=True, max_length=200)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounting.book')),
                ('cash_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounting.cashaccount')),
                ('currency', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounting.currencycategory')),
            ],
        ),
    ]
