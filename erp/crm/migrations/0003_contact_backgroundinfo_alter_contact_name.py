# Generated by Django 4.2.4 on 2025-06-25 06:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0002_remove_contact_company_name_alter_note_company_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='backgroundInfo',
            field=models.TextField(blank=True, max_length=400, verbose_name='Background info'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='name',
            field=models.CharField(max_length=200, verbose_name='Contact Name (required)'),
        ),
    ]
