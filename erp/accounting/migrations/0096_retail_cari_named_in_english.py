"""Name the shared retail cari in English, in the database.

The row is written by code, not typed by anyone — get_or_create_retail_cari
mints it on a fresh install and every walk-in sale posts to it — so its name
and notes are ours to state, and the database states things in English.
The Turkish label belongs in the interface, where gettext puts it.

Matched on ``code="PERAKENDE"``, which is what every lookup already uses;
the name is display text and nothing joins on it.
"""
from django.db import migrations

CODE = "PERAKENDE"

EN_NAME = "Retail Sales"
EN_NOTES = ("System account — anonymous retail sales are posted here "
            "automatically.")

TR_NAME = "Perakende Satışları"
TR_NOTES = ("Sistem carisi — anonim perakende satışlar otomatik buraya "
            "işlenir.")


def _rename(apps, name, notes):
    CariAccount = apps.get_model("accounting", "CariAccount")
    CariAccount.objects.filter(code=CODE).update(name=name, notes=notes)


def to_english(apps, schema_editor):
    _rename(apps, EN_NAME, EN_NOTES)


def back_to_turkish(apps, schema_editor):
    _rename(apps, TR_NAME, TR_NOTES)


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0095_chartaccount_journalentry_journalline_and_more'),
    ]

    operations = [
        migrations.RunPython(to_english, back_to_turkish),
    ]
