# Generated by Django 4.2.4 on 2023-09-30 14:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0007_remove_task_contact_company_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='days_since_due',
            field=models.IntegerField(default=0),
        ),
    ]
