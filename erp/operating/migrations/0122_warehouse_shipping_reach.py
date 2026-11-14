# Shipping reach on each warehouse (operating.shipping). Schema only: three
# columns with defaults, on a table of a few rows.

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0121_shippingrule'),
    ]

    operations = [
        migrations.AddField(
            model_name='warehouse',
            name='ships_to',
            field=models.CharField(choices=[('everywhere', 'Every country'), ('only', 'Only these countries'), ('except', 'Every country except these')], default='everywhere', max_length=10),
        ),
        migrations.AddField(
            model_name='warehouse',
            name='ships_to_countries',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=2), blank=True, default=list, size=None),
        ),
        migrations.AddField(
            model_name='warehouse',
            name='ships_best_to',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=2), blank=True, default=list, size=None),
        ),
    ]
