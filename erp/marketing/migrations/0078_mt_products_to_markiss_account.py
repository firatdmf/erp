"""Tag the remaining MT-xxxx products with the MARKİSS TEKSTİL account.

0077 moved the 13 MT-xxxx products that hung off Supplier #5. Nine more
(MT-1002, MT-1003, MT-1008, MT-1052, MT-1064, MT-1065, MT-5003, MT-5018,
MT-5019) carried no supplier at all, so nothing pointed them anywhere —
they're the same vendor's goods, confirmed by the people buying them.

Deliberately narrow: only MT- products that still have NO account. A
product already pointed somewhere is left alone, so re-running this can't
overwrite a later correction.
"""
from django.db import migrations


MARKISS_CARI_ID = 163
TITLE_PREFIX = "MT-"


def forwards(apps, schema_editor):
    Product = apps.get_model("marketing", "Product")
    CariAccount = apps.get_model("accounting", "CariAccount")

    if not CariAccount.objects.filter(pk=MARKISS_CARI_ID).exists():
        return          # different database — nothing to do

    Product.objects.filter(
        title__startswith=TITLE_PREFIX,
        supplier_account__isnull=True,
    ).update(supplier_account_id=MARKISS_CARI_ID)


def backwards(apps, schema_editor):
    """Untag exactly what forwards() could have tagged.

    This also clears the 13 that 0077 moved — they match the same filter
    and nothing distinguishes them at this point. 0077's own reverse step
    is what restores those, so unapplying the pair in order lands right.
    """
    Product = apps.get_model("marketing", "Product")
    Product.objects.filter(
        title__startswith=TITLE_PREFIX,
        supplier_account_id=MARKISS_CARI_ID,
    ).update(supplier_account=None)


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0077_product_supplier_account"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
