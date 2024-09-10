# Generated by Django 4.2.4 on 2024-08-10 00:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0013_remove_company_city_remove_company_state_and_more'),
        ('accounting', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='income',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crm.company'),
        ),
        migrations.AddField(
            model_name='income',
            name='contact',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='crm.contact'),
        ),
    ]
