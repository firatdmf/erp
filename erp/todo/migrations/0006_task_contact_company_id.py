# Generated by Django 4.2.4 on 2023-09-22 23:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('todo', '0005_rename_name_task_task_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='contact_company_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
