"""Add the Operations manager row, so it can be granted in the admin.

Nobody is given it here: who manages operations is decided per person.
"""
from django.db import migrations

NAME = "manager"


def seed(apps, schema_editor):
    Permission = apps.get_model("authentication", "Permission")
    Permission.objects.get_or_create(name=NAME, defaults={"description": NAME})


def unseed(apps, schema_editor):
    apps.get_model("authentication", "Permission").objects.filter(name=NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0023_operations_manager_label"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
