# Generated by Django 4.2.4 on 2024-11-30 18:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0011_product_created_at_product_manufacturer_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='created_at',
        ),
    ]
