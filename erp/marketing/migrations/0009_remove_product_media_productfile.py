# Generated by Django 4.2.4 on 2025-02-16 19:22

from django.db import migrations, models
import django.db.models.deletion
import marketing.models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0008_rename_supplier_product_vendor_product_tags'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='media',
        ),
        migrations.CreateModel(
            name='ProductFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=marketing.models.product_directory_path, validators=[marketing.models.validate_file_size, marketing.models.validate_file_type])),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='marketing.product')),
            ],
        ),
    ]
