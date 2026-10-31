# Dividends paid from a current account: the field, and cash_account made
# optional so that field can stand in its place. The rule that exactly one
# of the two is set comes in 0125, on its own.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0123_invoice_cancel_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='equitydivident',
            name='paid_by_current_account',
            field=models.ForeignKey(blank=True, help_text='Somebody who owes the book paid the owner directly. Leave the cash account blank; what they owe goes down instead.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='funded_dividends', to='accounting.currentaccount', verbose_name='Paid by (current account)'),
        ),
        migrations.AlterField(
            model_name='equitydivident',
            name='cash_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounting.cashaccount'),
        ),
    ]
