# Generated by Django 4.2.4 on 2024-11-30 17:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0008_product_stock_quantity_product_variant_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='variant',
        ),
    ]
