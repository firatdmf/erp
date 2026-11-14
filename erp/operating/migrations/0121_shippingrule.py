# Which countries may be sent goods from which (operating.shipping). A new
# table: no data, nothing else touched.

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0120_order_continued_from'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShippingRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('destination', models.CharField(max_length=2, unique=True)),
                ('only_from_inside', models.BooleanField(default=False)),
                ('not_from', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=2), blank=True, default=list, size=None)),
                ('best_from', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=2), blank=True, default=list, size=None)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['destination'],
            },
        ),
    ]
