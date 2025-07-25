# Generated by Django 4.2.4 on 2025-06-19 08:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0003_alter_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('in_production', 'In Production'), ('quality_check', 'Quality Check'), ('in_repair', 'In Repair'), ('ready', 'Ready for Shipment'), ('shipped', 'Shipped'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending', max_length=32),
        ),
    ]
