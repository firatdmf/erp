# Generated by Django 4.2.4 on 2025-02-14 09:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0016_product'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rawmaterial',
            name='supplierCompany',
        ),
        migrations.RemoveField(
            model_name='rawmaterial',
            name='supplierContact',
        ),
        migrations.RemoveField(
            model_name='rawmaterial',
            name='type',
        ),
        migrations.DeleteModel(
            name='Product',
        ),
        migrations.DeleteModel(
            name='RawMaterial',
        ),
        migrations.DeleteModel(
            name='RawMaterialCategory',
        ),
        migrations.DeleteModel(
            name='UnitCategory',
        ),
    ]
