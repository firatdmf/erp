# Generated by Django 4.2.4 on 2024-10-02 06:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0027_alter_stakeholder_book'),
    ]

    operations = [
        migrations.RenameField(
            model_name='stakeholder',
            old_name='book',
            new_name='books',
        ),
    ]
