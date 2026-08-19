from django.db import migrations


def seed_issuances(apps, schema_editor):
    """Give every existing holding a record explaining it.

    Holdings predate the issuance ledger, so their numbers have no
    history behind them. Without this the first recompute would floor
    every one of them to zero — the cache is derived from issuances now,
    and an empty ledger sums to nothing.
    """
    StakeholderBook = apps.get_model("accounting", "StakeholderBook")
    ShareIssuance = apps.get_model("accounting", "ShareIssuance")
    from django.utils import timezone

    today = timezone.now().date()
    for sb in StakeholderBook.objects.filter(shares__gt=0):
        if not ShareIssuance.objects.filter(stakeholder=sb).exists():
            ShareIssuance.objects.create(
                stakeholder=sb,
                shares=sb.shares,
                date=today,
                reason="opening",
                note="Holding as recorded before share issuances were tracked.",
            )


def drop_issuances(apps, schema_editor):
    ShareIssuance = apps.get_model("accounting", "ShareIssuance")
    ShareIssuance.objects.filter(reason="opening").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0070_shareissuance"),
    ]

    operations = [
        migrations.RunPython(seed_issuances, drop_issuances),
    ]
