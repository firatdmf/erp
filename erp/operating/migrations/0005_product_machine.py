# Generated by Django 4.2.4 on 2024-08-10 15:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0004_machine'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='machine',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='operating.machine'),
            preserve_default=False,
        ),
    ]
