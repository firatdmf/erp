from collections import defaultdict

from django.db import migrations


def file_each_product_with_its_business(apps, schema_editor):
    """Give every product the directory of the business that keeps it.

    Until now the catalogue was everybody's. A product is the business's
    whose shelves alone hold it: where every warehouse row of it stands in
    books of ONE directory, it is filed there. Everything else — held by
    several, or by none — stays with the oldest directory, which is the
    one every book read before a second existed.
    """
    Product = apps.get_model("marketing", "Product")
    if not Product.objects.exists():
        return
    Directory = apps.get_model("crm", "Directory")
    WarehouseProduct = apps.get_model("operating", "WarehouseProduct")
    main = Directory.objects.order_by("id").first() or Directory.objects.create(name="Main")

    held_in = defaultdict(set)
    rows = (WarehouseProduct.objects
            .filter(catalog_variant__isnull=False,
                    warehouse__accounting_book__directory__isnull=False)
            .values_list("catalog_variant__product_id",
                         "warehouse__accounting_book__directory_id").distinct())
    for product_id, directory_id in rows:
        held_in[product_id].add(directory_id)
    elsewhere = defaultdict(list)
    for product_id, directories in held_in.items():
        if len(directories) == 1:
            (only,) = directories
            if only != main.pk:
                elsewhere[only].append(product_id)

    Product.objects.filter(directory__isnull=True).update(directory=main)
    for directory_id, product_ids in elsewhere.items():
        Product.objects.filter(pk__in=product_ids).update(directory_id=directory_id)


class Migration(migrations.Migration):

    # Rows only — see 0097 for why this is not done there.
    dependencies = [
        ('crm', '0026_unique_names_per_directory'),
        ('accounting', '0115_book_directory'),
        ('operating', '0107_stockmovement_purpose_unpurchased'),
        ('marketing', '0097_product_directory'),
    ]

    operations = [
        migrations.RunPython(file_each_product_with_its_business, migrations.RunPython.noop),
    ]
