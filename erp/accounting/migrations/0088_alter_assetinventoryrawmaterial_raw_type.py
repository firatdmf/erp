# Generated by Django 4.2.4 on 2025-02-14 09:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0087_assetinventorygood_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assetinventoryrawmaterial',
            name='raw_type',
            field=models.CharField(choices=[('direct', 'Direct'), ('indirect', 'Indirect')], default=('direct', 'Direct')),
        ),
    ]
