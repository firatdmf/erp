"""Give everyone and every role holding "Middle manager" the permissions
it stood for, and remove it.

Middle manager meant: manage their books ("admin", which includes
confirming purchases), see cost and profit, print labels. Confirming
purchases is ticked too, so the role shows all it does. Nobody's access
changes: each check that accepted the old row accepts one of these.
"""
from django.db import migrations

OLD = "middle_manager"
INTO = ["admin", "purchase_confirm", "view_profit", "print_labels"]


def split(apps, schema_editor):
    Permission = apps.get_model("authentication", "Permission")
    Member = apps.get_model("authentication", "Member")
    Role = apps.get_model("authentication", "Role")
    old = Permission.objects.filter(name=OLD).first()
    if old is None:
        return
    into = [Permission.objects.get_or_create(name=name)[0] for name in INTO]
    for member in Member.objects.filter(permissions=old):
        member.permissions.add(*into)
    for role in Role.objects.filter(permissions=old):
        role.permissions.add(*into)
    old.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0032_middle_manager_is_a_role"),
    ]

    operations = [migrations.RunPython(split, migrations.RunPython.noop)]
