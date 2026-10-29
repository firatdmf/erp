"""Create the "Print labels" permission and grant it to everyone who
prints labels today.

Until now any member who could open a label's page could print it; only
the sales-rep role was kept away, and only from some of them, by the
pages it may open. Printing is now a grant of its own
(erp.roles.may_print_labels). Granting it here to every member NOT
carrying sales_rep means nobody else's screens change on deploy; it is
taken from or given to anyone from Django admin → Members.
"""
from django.db import migrations

NAME = "print_labels"
DESCRIPTION = "Can print stock, roll and package labels."


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
        ("authentication", "0029_print_labels_permission_choice"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
