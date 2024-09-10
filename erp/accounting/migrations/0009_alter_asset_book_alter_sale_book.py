# Generated by Django 4.2.4 on 2024-09-08 06:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0008_asset_book_sale_book'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='book',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='accounting.book'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='sale',
            name='book',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='accounting.book'),
            preserve_default=False,
        ),
    ]
