"""Give Prices and customers to every role that sees orders today.

Every role holding Orders gets it — a permission is always a role's,
never one person's. A role left without it writes the packing_only
restriction onto its members, the way a role without Orders writes
"manager" (authentication.member_roles): today that is only a role that
has no Orders either, so nobody's view of an order changes here. It
starts to mean something once a role holds Orders without this —
Operations, which packs and ships orders without their prices or
customer. See erp.roles.sees_order_money.
"""
from django.db import migrations

NAME = "prices_customers"
FLAG = "packing_only"
DESCRIPTION = ("Sees an order's prices, totals and payments, and its customer. "
               "Without it, an order shows what to pack and ship and where it goes.")


def seed(apps, schema_editor):
    Permission = apps.get_model("authentication", "Permission")
    Member = apps.get_model("authentication", "Member")
    Role = apps.get_model("authentication", "Role")
    row = Permission.objects.get_or_create(name=NAME, defaults={"description": DESCRIPTION})[0]
    flag = Permission.objects.get_or_create(
        name=FLAG, defaults={"description": "Set on whoever lacks the Prices and customers permission."})[0]
    for role in Role.objects.all():
        if role.permissions.filter(name="orders").exists():
            role.permissions.add(row)
            for member in Member.objects.filter(role=role):
                member.permissions.add(row)
        else:
            for member in Member.objects.filter(role=role):
                member.permissions.add(flag)


def unseed(apps, schema_editor):
    apps.get_model("authentication", "Permission").objects.filter(name__in=(NAME, FLAG)).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0036_prices_and_customers_choice"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
