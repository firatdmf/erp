# Generated by Django 4.2.4 on 2025-06-05 07:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0021_product_primary_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='productfile',
            name='is_primary',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='productfile',
            name='sequence',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
