# Generated by Django 4.2.4 on 2025-02-12 11:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0073_rename_stakeholder_equitydivident_member_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='equitydivident',
            options={'verbose_name_plural': 'Equity Dividents'},
        ),
        migrations.DeleteModel(
            name='Asset',
        ),
        migrations.DeleteModel(
            name='AssetCategory',
        ),
    ]
