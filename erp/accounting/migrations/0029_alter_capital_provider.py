# Generated by Django 4.2.4 on 2024-10-02 08:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0028_rename_book_stakeholder_books'),
    ]

    operations = [
        migrations.AlterField(
            model_name='capital',
            name='provider',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounting.stakeholder'),
        ),
    ]