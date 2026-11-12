# A follow-up order holds what was left when part of an order shipped
# (operating.partial_shipment). Schema only: a nullable column, no data.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0119_order_line_names_a_variant'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='continued_from',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='The order that shipped part of this request; this one holds the rest.',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='continuations', to='operating.order'),
        ),
    ]
