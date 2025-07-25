# Generated by Django 4.2.4 on 2025-06-18 12:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0002_order_orderitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('in_production', 'In Production'), ('quality_check', 'Quality Check'), ('in_repair', 'In Repair'), ('ready', 'Ready for Shipment'), ('shipped', 'Shipped'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending', max_length=32),
        ),
    ]
