# Generated by Django 4.2.4 on 2024-08-25 21:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0004_assetcategory_alter_asset_name_asset_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounting.assetcategory'),
        ),
    ]