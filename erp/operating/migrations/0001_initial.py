# Generated by Django 4.2.4 on 2024-08-10 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('crm', '0013_remove_company_city_remove_company_state_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RawMaterialCategorys',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('unit', models.CharField(default='piece', max_length=10)),
            ],
            options={
                'verbose_name_plural': 'Raw Material Categories',
            },
        ),
        migrations.CreateModel(
            name='RawMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('cost', models.DecimalField(decimal_places=2, max_digits=6)),
                ('supplierCompany', models.ManyToManyField(blank=True, to='crm.company')),
                ('supplierContact', models.ManyToManyField(blank=True, to='crm.contact')),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('variant', models.CharField(max_length=10)),
                ('cost', models.DecimalField(decimal_places=2, max_digits=6)),
                ('unit', models.CharField(default='piece', max_length=10)),
                ('raw_materials', models.ManyToManyField(to='operating.rawmaterial')),
            ],
        ),
    ]
