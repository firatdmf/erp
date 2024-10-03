# Generated by Django 4.2.4 on 2024-10-01 11:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0025_rename_shares_stakeholder_share'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stakeholder',
            name='book',
        ),
        migrations.AddField(
            model_name='stakeholder',
            name='book',
            field=models.ManyToManyField(to='accounting.book'),
        ),
    ]