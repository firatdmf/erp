# Generated by Django 4.2.4 on 2025-07-15 21:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0013_alter_orderitem_quantity'),
        ('accounting', '0003_remove_invoice_items_invoice_order'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoice',
            name='id',
        ),
        migrations.AlterField(
            model_name='invoice',
            name='order',
            field=models.OneToOneField(blank=True, default=1, on_delete=django.db.models.deletion.RESTRICT, primary_key=True, serialize=False, to='operating.order'),
            preserve_default=False,
        ),
    ]
