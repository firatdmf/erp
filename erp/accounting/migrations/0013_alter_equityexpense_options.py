# Generated by Django 4.2.4 on 2024-10-07 13:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0012_alter_equityexpense_cash_account'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='equityexpense',
            options={'verbose_name_plural': 'Equity Expenses'},
        ),
    ]
