# Generated by Django 4.2.4 on 2025-07-15 22:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0005_alter_assetaccountsreceivable_invoice'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assetaccountsreceivable',
            name='invoice',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accounts_receivables', to='accounting.invoice'),
        ),
    ]
