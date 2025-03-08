# Generated by Django 4.2.4 on 2025-03-07 21:17

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import marketing.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('crm', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('sku', models.CharField(blank=True, max_length=12, null=True)),
                ('barcode', models.CharField(blank=True, max_length=14, null=True)),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100), blank=True, default=list, size=None)),
                ('type', models.CharField(blank=True, null=True)),
                ('unit_of_measurement', models.CharField(blank=True, choices=[('units', 'Unit'), ('mt', 'Meter'), ('kg', 'Kilogram')], default=('units', 'Unit'), null=True)),
                ('quantity', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('cost', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('featured', models.BooleanField(default=True)),
                ('selling_while_out_of_stock', models.BooleanField(default=False)),
                ('weight', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('unit_of_weight', models.CharField(choices=[('lb', 'lb'), ('oz', 'oz'), ('kg', 'kg'), ('g', 'g')], default=('lb', 'lb'))),
            ],
        ),
        migrations.CreateModel(
            name='ProductCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProductCollection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('image', models.FileField(blank=True, null=True, upload_to=marketing.models.product_directory_path, validators=[marketing.models.validate_file_size, marketing.models.validate_image_type])),
            ],
        ),
        migrations.CreateModel(
            name='ProductVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variant_sku', models.CharField(blank=True, max_length=12, null=True)),
                ('variant_barcode', models.CharField(blank=True, max_length=14, null=True)),
                ('variant_quantity', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('variant_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('variant_cost', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('variant_featured', models.BooleanField(default=True)),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='marketing.product')),
            ],
            options={
                'verbose_name_plural': 'Product Variants',
            },
        ),
        migrations.CreateModel(
            name='ProductVariantAttribute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Attribute Name')),
            ],
        ),
        migrations.CreateModel(
            name='ProductFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='product_files/', validators=[marketing.models.validate_file_size, marketing.models.validate_file_type])),
                ('sequence', models.SmallIntegerField(unique=True)),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='files', to='marketing.product')),
                ('product_variant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='files', to='marketing.productvariant')),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='marketing.productcategory'),
        ),
        migrations.AddField(
            model_name='product',
            name='collections',
            field=models.ManyToManyField(blank=True, related_name='products', to='marketing.productcollection'),
        ),
        migrations.AddField(
            model_name='product',
            name='vendor',
            field=models.ManyToManyField(blank=True, related_name='products', to='crm.supplier'),
        ),
        migrations.CreateModel(
            name='ProductVariantAttributeValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=255, verbose_name='Attribute Value')),
                ('attribute', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketing.productvariantattribute')),
                ('variant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='attribute_values', to='marketing.productvariant')),
            ],
            options={
                'unique_together': {('variant', 'attribute')},
            },
        ),
    ]
