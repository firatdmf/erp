# Variants no longer carry attributes of their own (C120 deleted the last
# 706 rows). Only Django's picture of the table changes here: the code
# running while this deploys still reads product_variant_id, so the column
# and its index are dropped in a later release, once this one is live.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0118_product_gsm"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveIndex(
                    model_name="productattribute",
                    name="marketing_p_product_0910eb_idx",
                ),
                migrations.RemoveField(
                    model_name="productattribute",
                    name="product_variant",
                ),
            ],
            database_operations=[],
        ),
    ]
