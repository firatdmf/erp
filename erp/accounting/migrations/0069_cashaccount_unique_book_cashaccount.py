# Generated by Django 4.2.4 on 2025-02-11 12:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0068_remove_cashaccount_unique_book_cashaccount'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='cashaccount',
            constraint=models.UniqueConstraint(fields=('book', 'name'), name='unique_book_cashaccount'),
        ),
    ]
