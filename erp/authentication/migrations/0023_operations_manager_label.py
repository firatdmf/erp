"""Call the unused "manager" access level Operations manager.

Choices only: the stored name stays "manager", so nothing in the table
changes. See erp.roles.ORDER_PREFIXES.
"""
from django.db import migrations, models

CHOICES = [
    ("admin", "Admin"), ("manager", "Operations manager"), ("employee", "Employee"),
    ("guest", "Guest"), ("purchase_confirm", "Confirm purchases"),
    ("sales_rep", "Sales rep (read-only)"),
    ("view_profit", "See cost and profit"),
    ("middle_manager", "Middle manager"),
]
DESCRIPTIONS = [
    ("admin", "Has full access to all resources and settings."),
    ("manager", "Works the warehouse and its stock. Cannot see or create orders."),
    ("employee", "Can access and manage their own tasks and projects."),
    ("guest", "Has limited access to view certain resources."),
    ("purchase_confirm", "Can confirm a purchase order into warehouse stock (goods receipt)."),
    ("sales_rep", "Can view stock quantities, prices and sales. Cannot change anything."),
    ("view_profit", "Can see cost of goods, gross profit and margin on orders and analytics."),
    ("middle_manager", "Manages the books they are assigned: warehouses, orders, purchases, costs and profit. Nothing install-wide, nothing of another business."),
]


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0022_middle_manager"),
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
