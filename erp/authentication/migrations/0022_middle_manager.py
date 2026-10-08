"""Add the Middle manager user type.

One row for whoever runs one business on an install that carries several:
it manages the books it is assigned, confirms their purchases and sees
their costs, and reaches nothing install-wide. See erp.roles.is_middle_manager.
"""
from django.db import migrations, models

NAME = "middle_manager"

CHOICES = [
    ("admin", "Admin"), ("manager", "Manager"), ("employee", "Employee"),
    ("guest", "Guest"), ("purchase_confirm", "Confirm purchases"),
    ("sales_rep", "Sales rep (read-only)"),
    ("view_profit", "See cost and profit"),
    ("middle_manager", "Middle manager"),
]
DESCRIPTIONS = [
    ("admin", "Has full access to all resources and settings."),
    ("manager", "Can manage teams and projects, but has limited access to settings."),
    ("employee", "Can access and manage their own tasks and projects."),
    ("guest", "Has limited access to view certain resources."),
    ("purchase_confirm", "Can confirm a purchase order into warehouse stock (goods receipt)."),
    ("sales_rep", "Can view stock quantities, prices and sales. Cannot change anything."),
    ("view_profit", "Can see cost of goods, gross profit and margin on orders and analytics."),
    ("middle_manager", "Manages the books they are assigned: warehouses, orders, purchases, costs and profit. Nothing install-wide, nothing of another business."),
]


def seed(apps, schema_editor):
    Permission = apps.get_model("authentication", "Permission")
    Permission.objects.get_or_create(name=NAME, defaults={"description": NAME})


def unseed(apps, schema_editor):
    apps.get_model("authentication", "Permission").objects.filter(name=NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0021_seed_view_profit_permission"),
    ]

    operations = [
        migrations.AlterField(
            model_name="permission",
            name="name",
            field=models.CharField(choices=CHOICES, max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name="permission",
            name="description",
            field=models.TextField(blank=True, choices=DESCRIPTIONS, null=True),
        ),
        migrations.RunPython(seed, unseed),
    ]
