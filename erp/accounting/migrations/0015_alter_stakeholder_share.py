# Generated by Django 4.2.4 on 2024-10-15 18:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0014_stakeholder_share'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stakeholder',
            name='share',
            field=models.DecimalField(decimal_places=2, default=100, max_digits=5),
        ),
    ]
