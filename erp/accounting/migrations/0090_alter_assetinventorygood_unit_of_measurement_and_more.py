# Generated by Django 4.2.4 on 2025-02-14 09:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0089_alter_assetinventorygood_unit_of_measurement_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assetinventorygood',
            name='unit_of_measurement',
            field=models.CharField(blank=True, choices=[('mt', 'Meter'), ('kg', 'Kilogram'), ('units', 'Units')], null=True),
        ),
        migrations.AlterField(
            model_name='assetinventoryrawmaterial',
            name='unit_of_measurement',
            field=models.CharField(blank=True, choices=[('mt', 'Meter'), ('kg', 'Kilogram'), ('units', 'Units')], null=True),
        ),
    ]
