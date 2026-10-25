"""Fill Product.tracking from what the unit used to decide.

Until now a product was sold by count exactly when its unit was piece or
pack, so those start tracked by variant and everything else by each item:
nothing on screen changes until somebody sets a product differently.
"""
from django.db import migrations


def fill(apps, schema_editor):
    Product = apps.get_model("marketing", "Product")
    Product.objects.filter(unit__in=["piece", "pack"]).update(tracking="variant")


def unfill(apps, schema_editor):
    Product = apps.get_model("marketing", "Product")
    Product.objects.update(tracking="item")


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0116_product_tracking"),
    ]

    operations = [
        migrations.RunPython(fill, unfill),
    ]
