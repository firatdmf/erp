# Every order line names its variant. Prod had one line without (order
# 385's, a test web order deleted as O17 before this ran), so this only
# sets NOT NULL; it moves no data.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0118_product_gsm'),
        ('operating', '0118_drop_order_original_snapshot'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='product_variant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                    to='marketing.productvariant'),
        ),
    ]
