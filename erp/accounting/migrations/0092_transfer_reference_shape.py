"""Give the transfers already on the ledger the reference shape the rest of
the ledger uses.

"TRANSFER 4" was written by CariTransfer.post() before it had a reference
of its own. It sat in the Reference column beside COL-2026-000052 and
PUR-2026-000093 saying neither what it was nor when.

Only the two legs of a transfer are touched, and only their `reference`
text. Nothing about the amounts, the accounts or the balances moves — a
reference is how a row is cited, not what it is worth.

Purchase invoice NUMBERS are deliberately not renumbered here. Those are
issued documents; new ones are cut as PUR-… from now on, and the ones
already written keep the identity they were issued under.
"""
from django.db import migrations


def _ref(transfer):
    return f"TRA-{transfer.date.year}-{str(transfer.pk).zfill(6)}"


def forwards(apps, schema_editor):
    CariTransfer = apps.get_model("accounting", "CariTransfer")
    CariMovement = apps.get_model("accounting", "CariMovement")
    for transfer in CariTransfer.objects.all().iterator():
        legs = [pk for pk in (transfer.from_movement_id, transfer.to_movement_id) if pk]
        if legs:
            CariMovement.objects.filter(pk__in=legs).update(reference=_ref(transfer))


def backwards(apps, schema_editor):
    CariTransfer = apps.get_model("accounting", "CariTransfer")
    CariMovement = apps.get_model("accounting", "CariMovement")
    for transfer in CariTransfer.objects.all().iterator():
        legs = [pk for pk in (transfer.from_movement_id, transfer.to_movement_id) if pk]
        if legs:
            CariMovement.objects.filter(pk__in=legs).update(
                reference=f"TRANSFER {transfer.pk}")


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0091_alter_carimovement_exchange_rate_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
