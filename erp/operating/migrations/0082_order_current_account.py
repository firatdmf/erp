"""Order.cari follows accounting's rename.

A rename, not a drop and an add: the autodetector proposed removing `cari`
and adding `current_account`, which would have thrown away which account
every order in the book belongs to.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0081_stock_item_related_names"),
        ("accounting", "0098_rename_cari_to_current_account"),
    ]

    operations = [
        migrations.RenameField("order", "cari", "current_account"),
    ]
