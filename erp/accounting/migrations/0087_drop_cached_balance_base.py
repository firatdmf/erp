"""Drop CariAccount.cached_balance_base — a verbatim copy of cached_balance.

recompute_balance() set both columns from the same expression, and the
account list summed one while filtering on the other. Correct only for as
long as the two agreed, which nothing enforced — the same shape as the
balance/statement split that migration 0086 removed, one level down.

Verified identical on all 1,283 accounts before this was written, and the
two figures the list page shows (owes_us 1,493,951.43 / we_owe
-1,145,383.07) come out the same to the cent from either column.

Reversible: the column comes back with its 0.00 default, and the next
recompute_balance() on an account would have refilled it anyway.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0086_carimovement_is_void'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cariaccount',
            name='cached_balance_base',
        ),
    ]
