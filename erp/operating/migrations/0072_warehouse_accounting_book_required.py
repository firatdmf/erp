"""A warehouse must say which book owns its stock.

The link was optional, and "no book" meant the warehouse was visible to
every member and searchable from every order — the one row that had no
book (Ortak Perde Depo) was shown to everyone regardless of which
business they work for. Who may read a shelf, which orders may draw on
it and whose net worth it counts toward all follow from this field, so
it is not something a warehouse gets to leave blank.

Every existing row already names a book, so the NOT NULL applies
cleanly; the guard below fails loudly rather than letting the ALTER
crash half way if that ever stops being true.

on_delete moves from SET_NULL to PROTECT for the same reason: there is
no longer a null to fall back to, and a book holding stock should not be
deletable out from under it.
"""
from django.db import migrations, models
import django.db.models.deletion


def refuse_bookless_warehouses(apps, schema_editor):
    Warehouse = apps.get_model("operating", "Warehouse")
    orphans = list(
        Warehouse.objects.filter(accounting_book__isnull=True)
        .values_list("pk", "name")
    )
    if orphans:
        raise RuntimeError(
            "These warehouses have no accounting_book and the column is "
            "about to become NOT NULL. Assign each one its book, then "
            "re-run: %s" % ", ".join(f"#{pk} {name}" for pk, name in orphans)
        )


def noop(apps, schema_editor):
    """Nothing to undo — the check writes nothing."""


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0071_order_billed_line_quantities_and_more"),
        ("accounting", "0094_remove_book_only_one_default_cari_target_book_and_more"),
    ]

    operations = [
        migrations.RunPython(refuse_bookless_warehouses, noop),
        migrations.AlterField(
            model_name="warehouse",
            name="accounting_book",
            field=models.ForeignKey(
                help_text="Accounting book this warehouse's stock belongs to",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="warehouses",
                to="accounting.book",
            ),
        ),
    ]
