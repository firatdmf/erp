import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0107_stockmovement_purpose_unpurchased"),
    ]

    operations = [
        migrations.AlterField(
            model_name="warehouseproduct",
            name="catalog_variant",
            field=models.ForeignKey(
                blank=True, null=True,
                help_text="The catalog variant this stock is.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="warehouse_products",
                to="marketing.productvariant",
            ),
        ),
        migrations.AddConstraint(
            model_name="warehouseproduct",
            constraint=models.UniqueConstraint(
                fields=("warehouse", "catalog_variant"),
                name="operating_warehouseproduct_one_row_per_variant",
            ),
        ),
    ]
