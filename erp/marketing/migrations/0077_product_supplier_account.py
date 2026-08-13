"""Point Product at the CARI ACCOUNT it's purchased from, not a crm.Supplier.

Suppliers and accounts were two parallel namespaces for the same vendors.
The accounts carry the balances (most were imported from KARVEN with no
Supplier row), warehouse intake posts purchases to accounts, and a product
tagged with a Supplier often pointed at a record with no account behind it.

Data move, in order of preference per product:
  1. the cari already linked to that supplier (CariAccount.supplier FK), else
  2. an explicit override for vendors whose account was never linked.

MARKISS is the override case that prompted this: its 13 MT-xxxx products
hung off Supplier #5, whose only account was an empty duplicate — the real
balance has always been on "MARKİSS TEKSTİL" (#163). Name matching can't
find it ("MARKISS" vs "MARKİSS TEKSTİL"), so the pairing is stated here.
Every step is existence-checked, so this is a no-op on a database that
doesn't have these rows.
"""
from django.db import migrations, models
import django.db.models.deletion


# supplier pk -> cari account pk, for vendors with no CariAccount.supplier link.
EXPLICIT_SUPPLIER_TO_CARI = {
    5: 163,   # MARKISS -> MARKİSS TEKSTİL
}


def forwards(apps, schema_editor):
    Product = apps.get_model("marketing", "Product")
    CariAccount = apps.get_model("accounting", "CariAccount")

    # supplier_id -> cari_id, from the link the accounts already carry.
    linked = dict(
        CariAccount.objects
        .filter(supplier_id__isnull=False)
        .values_list("supplier_id", "id")
    )

    mapping = dict(linked)
    for supplier_id, cari_id in EXPLICIT_SUPPLIER_TO_CARI.items():
        if CariAccount.objects.filter(pk=cari_id).exists():
            mapping[supplier_id] = cari_id

    for supplier_id, cari_id in mapping.items():
        Product.objects.filter(supplier_id=supplier_id).update(
            supplier_account_id=cari_id)


def backwards(apps, schema_editor):
    """Re-derive the supplier from the account's own supplier link.

    Products whose account has no supplier (the override cases) simply come
    back with an empty supplier — the same state they'd have been left in
    had the account never been linked, and nothing depends on the value.
    """
    Product = apps.get_model("marketing", "Product")
    CariAccount = apps.get_model("accounting", "CariAccount")

    reverse = dict(
        CariAccount.objects
        .filter(supplier_id__isnull=False)
        .values_list("id", "supplier_id")
    )
    for cari_id, supplier_id in reverse.items():
        Product.objects.filter(supplier_account_id=cari_id).update(
            supplier_id=supplier_id)


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0076_remove_productcategory_washing_instructions_and_more"),
        ("accounting", "0067_move_cari_content_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="supplier_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="products",
                to="accounting.cariaccount",
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name="product",
            name="supplier",
        ),
    ]
