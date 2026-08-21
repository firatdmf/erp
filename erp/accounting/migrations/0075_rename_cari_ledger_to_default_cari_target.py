"""Rename is_cari_ledger → is_default_cari_target.

0074 called the flag "the current-account ledger", which reads as though
one book is the ledger and the others are not. They are all ledgers —
one per business, and more are coming. The flag only marks which book a
new customer account or invoice falls into when the caller has not said,
so it is named for that.

A rename rather than a drop-and-add: 0074 is already applied in
production and the column carries a value there.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0074_book_is_cari_ledger_book_only_one_cari_ledger_book"),
    ]

    operations = [
        # The constraint names the column, so it comes off first and
        # goes back on after — Postgres will not follow the rename.
        migrations.RemoveConstraint(
            model_name="book",
            name="only_one_cari_ledger_book",
        ),
        migrations.RenameField(
            model_name="book",
            old_name="is_cari_ledger",
            new_name="is_default_cari_target",
        ),
        migrations.AlterField(
            model_name="book",
            name="is_default_cari_target",
            field=models.BooleanField(
                default=False,
                help_text="New customer accounts and invoices land in this "
                          "book when nothing else says which. Only one book "
                          "can hold it.",
                verbose_name="Default for new customer accounts",
            ),
        ),
        migrations.AddConstraint(
            model_name="book",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_default_cari_target", True)),
                fields=("is_default_cari_target",),
                name="only_one_default_cari_target_book",
            ),
        ),
    ]
