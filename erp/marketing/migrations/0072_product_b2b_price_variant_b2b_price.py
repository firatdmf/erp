from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0071_rename_websubscription_and_english_verbose'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='b2b_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Wholesale price shown on the B2B storefront. Leave blank to use the retail price.',
                max_digits=10,
                null=True,
                verbose_name='B2B Price',
            ),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='variant_b2b_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Wholesale price for this variant. Leave blank to inherit from product.',
                max_digits=10,
                null=True,
                verbose_name='Variant B2B Price',
            ),
        ),
    ]
