# Schema only; 0110 fills it in. The database keeps a default of '' so the
# release before this one, still serving while it deploys, can go on
# inserting products and groups without knowing the column.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0108_spell_meter_the_american_way'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='price_multiplier',
            field=models.CharField(blank=True, default='', help_text="Price = cost × this — left blank, the product group's applies", max_length=40),
        ),
        migrations.AddField(
            model_name='productcategory',
            name='price_multiplier',
            field=models.CharField(blank=True, default='', help_text='Price = cost × this, e.g. 4/3', max_length=40),
        ),
        migrations.RunSQL(
            sql=[
                "ALTER TABLE marketing_product ALTER COLUMN price_multiplier SET DEFAULT ''",
                "ALTER TABLE marketing_productcategory ALTER COLUMN price_multiplier SET DEFAULT ''",
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
