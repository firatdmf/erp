# Generated by Django 4.2.4 on 2025-02-20 16:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0015_productvariantattribute_productvariantattributevalue'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='productvariant',
            options={'verbose_name': 'Product Variant', 'verbose_name_plural': 'Product Variants'},
        ),
        migrations.RemoveField(
            model_name='productvariant',
            name='title',
        ),
    ]
