# Generated by Django 4.2.4 on 2023-10-07 12:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_alter_member_user'),
    ]

    operations = [
        migrations.RenameField(
            model_name='member',
            old_name='company',
            new_name='company_name',
        ),
    ]
