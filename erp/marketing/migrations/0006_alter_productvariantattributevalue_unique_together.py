# Generated by Django 4.2.4 on 2025-03-13 13:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0005_alter_product_supplier'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='productvariantattributevalue',
            unique_together=set(),
        ),
    ]
