# Generated by Django 4.2.4 on 2025-03-13 14:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0006_alter_productvariantattributevalue_unique_together'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='productvariantattributevalue',
            unique_together={('variant', 'attribute')},
        ),
    ]
