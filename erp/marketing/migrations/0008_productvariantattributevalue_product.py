# Generated by Django 4.2.4 on 2025-03-13 18:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0007_alter_productvariantattributevalue_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvariantattributevalue',
            name='product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='variant_attribute_values', to='marketing.product'),
        ),
    ]
