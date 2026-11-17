"""Give Accounts and customers to every role there is today.

Current accounts, payments, the ledger and the customer lists used to
come with Beyond sales (and a sales rep's customer lists with her role),
so every role keeps them and nobody's access changes here. The
permission starts to mean something once a role is left without it —
Operations, which runs warehouses and purchases without the money or
the people. See erp.roles.ACCOUNTS_PREFIXES.
"""
from django.db import migrations

NAME = "accounts_customers"
DESCRIPTION = ("Current accounts, payments, checks, the ledger and its reports, and "
               "the customer and supplier lists.")


def seed(apps, schema_editor):
    Permission = apps.get_model("authentication", "Permission")
    Member = apps.get_model("authentication", "Member")
    Role = apps.get_model("authentication", "Role")
    row = Permission.objects.get_or_create(name=NAME, defaults={"description": DESCRIPTION})[0]
    for role in Role.objects.all():
        role.permissions.add(row)
        for member in Member.objects.filter(role=role):
            member.permissions.add(row)


def unseed(apps, schema_editor):
    apps.get_model("authentication", "Permission").objects.filter(
        name__in=(NAME, "no_accounts")).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0038_accounts_and_customers_choice"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
