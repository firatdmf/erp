# Generated by Django 4.2.4 on 2024-11-16 23:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0018_alter_equityexpense_balance'),
    ]

    operations = [
        migrations.RenameField(
            model_name='equityexpense',
            old_name='balance',
            new_name='account_balance',
        ),
    ]
