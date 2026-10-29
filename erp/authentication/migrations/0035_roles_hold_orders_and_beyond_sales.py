"""Turn the Sales rep and Operations manager flags into what a role leaves
out, and drop Employee and Guest.

A role holding "sales_rep" now simply lacks Beyond sales; one holding
"manager" lacks Orders; every other role gets both. Its members then hold
its permissions plus the restriction of each one it lacks, which is what
they held before — nobody's access changes. A member in no role gets the
two permissions too, unless restricted, so the board shows them right.
"""
from django.db import migrations

RESTRICTIONS = {"manager": "orders", "sales_rep": "beyond_sales"}
DESCRIPTIONS = {
    "orders": "Sees and takes orders. Without it, no order is shown at all.",
    "beyond_sales": "Warehouses, purchases, accounts and the catalog. Without it, only looking up stock and customers and taking orders, with prices shown in place of cost.",
}


def move(apps, schema_editor):
    Permission = apps.get_model("authentication", "Permission")
    Member = apps.get_model("authentication", "Member")
    Role = apps.get_model("authentication", "Role")
    row = {name: Permission.objects.get_or_create(name=name, defaults={"description": d})[0]
           for name, d in DESCRIPTIONS.items()}
    flag = {name: Permission.objects.get_or_create(name=name)[0] for name in RESTRICTIONS}

    for role in Role.objects.all():
        names = set(role.permissions.values_list("name", flat=True))
        for restriction, grant in RESTRICTIONS.items():
            if restriction in names:
                role.permissions.remove(flag[restriction])
            else:
                role.permissions.add(row[grant])
        granted = set(role.permissions.values_list("name", flat=True))
        held = list(role.permissions.all()) + [
            flag[r] for r, g in RESTRICTIONS.items() if g not in granted]
        for member in Member.objects.filter(role=role):
            member.permissions.set(held)

    for member in Member.objects.filter(role__isnull=True, user__isnull=False):
        names = set(member.permissions.values_list("name", flat=True))
        for restriction, grant in RESTRICTIONS.items():
            if restriction not in names:
                member.permissions.add(row[grant])

    Permission.objects.filter(name__in=("employee", "guest")).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0034_orders_and_beyond_sales"),
    ]

    operations = [migrations.RunPython(move, migrations.RunPython.noop)]
