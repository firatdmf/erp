# Generated by Django 4.2.4 on 2024-10-06 06:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0005_rename_cashcategory_cashaccouns_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CashAccouns',
            new_name='CashAccounts',
        ),
    ]
