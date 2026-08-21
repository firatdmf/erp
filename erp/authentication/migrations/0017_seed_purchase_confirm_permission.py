"""Create the "Confirm purchases" permission and grant it to mirzael.

The gate itself (accounting.views_purchase.can_confirm_purchase) answers
yes to admins regardless; this row is what lets it be granted to someone
who is NOT an admin. Assigning it to mirzael here rather than leaving a
manual step means the flow works the moment it deploys — anyone else is
granted the same permission from Django admin → Members.
"""
from django.db import migrations

NAME = "purchase_confirm"
DESCRIPTION = "Can confirm a purchase order into warehouse stock (goods receipt)."
GRANT_TO = ["mirzael"]


def seed(apps, schema_editor):
    Permission = apps.get_model("authentication", "Permission")
    Member = apps.get_model("authentication", "Member")
    perm, _ = Permission.objects.get_or_create(
        name=NAME, defaults={"description": DESCRIPTION})
    for username in GRANT_TO:
        member = Member.objects.filter(user__username=username).first()
        if member is not None:
            member.permissions.add(perm)


def unseed(apps, schema_editor):
    Permission = apps.get_model("authentication", "Permission")
    Permission.objects.filter(name=NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0016_alter_permission_description_alter_permission_name"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
