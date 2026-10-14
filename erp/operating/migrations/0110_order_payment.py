# A payment taken for an order, tied to it by key (OrderPayment). A new
# table only: nothing existing is altered or rewritten.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0116_capital_paid_in_goods'),
        ('operating', '0109_spell_meter_the_american_way'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_links', to='operating.order')),
                ('payment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='order_link', to='accounting.payment')),
            ],
        ),
    ]
