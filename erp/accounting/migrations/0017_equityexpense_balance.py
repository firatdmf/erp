# Generated by Django 4.2.4 on 2024-11-16 22:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0016_delete_transaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='equityexpense',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
    ]
