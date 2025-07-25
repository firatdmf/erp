# Generated by Django 4.2.4 on 2025-06-13 09:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0028_alter_product_created_at'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productfile',
            name='file',
        ),
        migrations.AddField(
            model_name='productfile',
            name='file_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='productfile',
            name='is_primary',
            field=models.BooleanField(default=False),
        ),
    ]
