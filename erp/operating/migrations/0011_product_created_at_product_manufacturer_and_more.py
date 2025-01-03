# Generated by Django 4.2.4 on 2024-11-30 18:11

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0010_alter_product_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='manufacturer',
            field=models.CharField(default='ALPASLAN', max_length=250),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='product',
            name='variant',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='raw_materials',
            field=models.ManyToManyField(blank=True, to='operating.rawmaterial'),
        ),
        migrations.AlterField(
            model_name='product',
            name='sku',
            field=models.CharField(max_length=50),
        ),
    ]