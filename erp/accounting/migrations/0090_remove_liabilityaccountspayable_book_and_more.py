"""Drop the legacy AR/AP mirror tables.

They held nothing that was not already a CariMovement: 493 receivable rows
and 10 payable rows, every one written by the post_save mirror and
back-referenced by legacy_ar_id / legacy_ap_id, which go with them. Nothing
read them — the accounting equation deliberately summed
CariAccount.cached_balance instead, because the mirror skipped any payable
whose account carried no supplier FK and never netted the rows it did
write.

Irreversible on purpose: re-adding the tables would restore the columns but
not the rows, and a half-populated mirror is worse than no mirror.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0089_equityexpense_paid_by_cari_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='liabilityaccountspayable',
            name='book',
        ),
        migrations.RemoveField(
            model_name='liabilityaccountspayable',
            name='currency',
        ),
        migrations.RemoveField(
            model_name='liabilityaccountspayable',
            name='finished_goods_receipt',
        ),
        migrations.RemoveField(
            model_name='liabilityaccountspayable',
            name='paid_with_cash_account',
        ),
        migrations.RemoveField(
            model_name='liabilityaccountspayable',
            name='raw_material_good_receipt',
        ),
        migrations.RemoveField(
            model_name='liabilityaccountspayable',
            name='supplier',
        ),
        migrations.RemoveField(
            model_name='carimovement',
            name='legacy_ap_id',
        ),
        migrations.RemoveField(
            model_name='carimovement',
            name='legacy_ar_id',
        ),
        migrations.DeleteModel(
            name='AssetAccountsReceivable',
        ),
        migrations.DeleteModel(
            name='LiabilityAccountsPayable',
        ),
    ]
