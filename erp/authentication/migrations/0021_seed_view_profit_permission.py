"""Create the "See cost and profit" permission and grant it to everyone
who could already see those numbers.

Until now cost, COGS and gross profit were hidden from the sales-rep
role and shown to every other member. The gate is now a grant of its
own (erp.roles.may_see_profit), so the numbers can be given to or taken
from a member without touching what else they may do. Granting it here
to every member NOT carrying sales_rep means nobody's page changes on
deploy; anyone joining later is granted it from Django admin → Members.
"""
from django.db import migrations

NAME = "view_profit"
DESCRIPTION = "Can see cost of goods, gross profit and margin on orders and analytics."


def seed(apps, schema_editor):
    Permission = apps.get_model("authentication", "Permission")
    Member = apps.get_model("authentication", "Member")
    perm, _ = Permission.objects.get_or_create(
        name=NAME, defaults={"description": DESCRIPTION})
    for member in (Member.objects.filter(user__isnull=False)
                   .exclude(permissions__name="sales_rep")):
        member.permissions.add(perm)


def unseed(apps, schema_editor):
    Permission = apps.get_model("authentication", "Permission")
    Permission.objects.filter(name=NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0020_view_profit_permission_choice"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
