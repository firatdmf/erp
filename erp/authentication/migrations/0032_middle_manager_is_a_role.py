"""Drop "Middle manager" from the permissions, and call "admin" what it is.

Middle manager was never a permission of its own: it stood for managing
one's books, confirming purchases, seeing cost and profit and printing
labels, handed out together. Now that roles hold permissions together
(Role, 0031), it is a role made of those, and 0033 turns every holder of
it into them. "admin" is relabelled for what it does — manage the books a
member is assigned — since it never gave full access to anything.

Choices only: nothing in the table changes here.
"""
from django.db import migrations, models

CHOICES = [
    ("admin", "Manage their books"), ("manager", "Operations manager"), ("employee", "Employee"),
    ("guest", "Guest"), ("purchase_confirm", "Confirm purchases"),
    ("sales_rep", "Sales rep (read-only)"),
    ("view_profit", "See cost and profit"),
    ("print_labels", "Print labels"),
]
DESCRIPTIONS = [
    ("admin", "Manages the warehouses, orders and purchases of the books they are assigned, confirming purchases included. Nothing install-wide."),
    ("manager", "Works the warehouse and its stock. Cannot see or create orders."),
    ("employee", "Can access and manage their own tasks and projects."),
    ("guest", "Has limited access to view certain resources."),
    ("purchase_confirm", "Can confirm a purchase order into warehouse stock (goods receipt)."),
    ("sales_rep", "Can view stock quantities, prices and sales. Cannot change anything."),
    ("view_profit", "Can see cost of goods, gross profit and margin on orders and analytics."),
    ("print_labels", "Can print stock, roll and package labels."),
]


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0031_roles"),
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
    ]
