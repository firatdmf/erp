# Generated by Django 4.2.4 on 2025-02-07 21:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_rename_company_member_company_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='member',
            name='company_name',
        ),
    ]
