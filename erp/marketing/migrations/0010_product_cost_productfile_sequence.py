# Generated by Django 4.2.4 on 2025-02-16 19:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0009_remove_product_media_productfile'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='productfile',
            name='sequence',
            field=models.SmallIntegerField(default=1, unique=True),
        ),
    ]
