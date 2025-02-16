# Generated by Django 4.2.4 on 2025-02-11 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0063_alter_assetcash_options_alter_transaction_type_pk'),
    ]

    operations = [
        migrations.RenameField(
            model_name='equitycapital',
            old_name='stakeholder',
            new_name='member',
        ),
        migrations.RemoveField(
            model_name='stakeholderbook',
            name='equity_percentage',
        ),
        migrations.AlterField(
            model_name='assetcash',
            name='balance',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='equitycapital',
            name='note',
            field=models.TextField(blank=True, null=True),
        ),
    ]
