from django.db import migrations


def fix_unit_values(apps, schema_editor):
    Product = apps.get_model('marketing', 'Product')
    updated = Product.objects.filter(unit_of_measurement='meters').update(unit_of_measurement='mt')
    if updated:
        print(f"  Updated {updated} products: meters -> mt")


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0063_alt_text_null_true'),
    ]

    operations = [
        migrations.RunPython(fix_unit_values, migrations.RunPython.noop),
    ]
