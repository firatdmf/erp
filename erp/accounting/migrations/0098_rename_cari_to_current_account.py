"""Cari becomes current account.

"Cari hesap" is the Turkish for a running account with a customer or a
supplier, and the code had taken the first word of it as a type name. The
UI never did — its English already says "Account", and only the Turkish
says "Cari", which is correct there and stays. This makes the code agree
with the screens.

Renames only: every table keeps its rows, every column its values, every
foreign key its target. `cari` on Invoice, Payment, Order, JournalLine,
CheckOrPromissoryNote and the movement itself all become current_account;
CariSettings' three numbering columns and CariTransfer's two ends follow
the same word.

Order matters. The models are renamed first, so the field renames beneath
them address the new names.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0097_retail_auto_collection_desc_in_english"),
        # These two still name accounting.cariaccount as a FK target, and
        # the graph left them unordered against this migration, so a build
        # from scratch could rename the model out from under them:
        #
        #   ValueError: Related model 'accounting.cariaccount'
        #   cannot be resolved
        #
        # The same undeclared-edge shape as marketing/0080 and
        # operating/0076. They have to land while the old name still means
        # something.
        ("marketing", "0078_mt_products_to_markiss_account"),
        ("operating", "0068_alter_order_cari_and_more"),
        ("current_account", "0012_remove_carimovement_book_remove_carimovement_cari_and_more"),
    ]

    operations = [
        migrations.RenameModel("CariAccount", "CurrentAccount"),
        migrations.RenameModel("CariMovement", "CurrentAccountMovement"),
        migrations.RenameModel("CariSettings", "CurrentAccountSettings"),
        migrations.RenameModel("CariTransfer", "CurrentAccountTransfer"),

        migrations.RenameField("currentaccountmovement", "cari", "current_account"),
        migrations.RenameField("invoice", "cari", "current_account"),
        migrations.RenameField("payment", "cari", "current_account"),
        migrations.RenameField("journalline", "cari", "current_account"),
        migrations.RenameField("checkorpromissorynote", "cari", "current_account"),
        migrations.RenameField("equityexpense", "paid_by_cari",
                               "paid_by_current_account"),

        migrations.RenameField("currentaccounttransfer", "from_cari",
                               "from_current_account"),
        migrations.RenameField("currentaccounttransfer", "to_cari",
                               "to_current_account"),

        migrations.RenameField("currentaccountsettings", "cari_code_prefix",
                               "current_account_code_prefix"),
        migrations.RenameField("currentaccountsettings", "cari_code_padding",
                               "current_account_code_padding"),
        migrations.RenameField("currentaccountsettings", "next_cari_seq",
                               "next_current_account_seq"),
    ]
