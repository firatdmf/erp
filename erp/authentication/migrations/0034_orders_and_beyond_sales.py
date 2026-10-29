"""Orders and Beyond sales become permissions; Employee and Guest go.

Sales rep and Operations manager are roles, not permissions: each is a
role that leaves one permission out — Beyond sales, Orders. The two old
rows stay as the restrictions the checks read, written by a role onto its
members (authentication.member_roles), and are relabelled for that.
Employee and Guest were never checked anywhere.

Choices only: the rows are moved in 0035.
"""
from django.db import migrations, models

CHOICES = [
    ("orders", "Orders"), ("beyond_sales", "Beyond sales"),
    ("admin", "Manage their books"), ("purchase_confirm", "Confirm purchases"),
    ("view_profit", "See cost and profit"), ("print_labels", "Print labels"),
    ("manager", "No orders"), ("sales_rep", "Sales only"),
]
DESCRIPTIONS = [
    ("orders", "Sees and takes orders. Without it, no order is shown at all."),
    ("beyond_sales", "Warehouses, purchases, accounts and the catalog. Without it, only looking up stock and customers and taking orders, with prices shown in place of cost."),
    ("admin", "Manages the warehouses, orders and purchases of the books they are assigned, confirming purchases included. Nothing install-wide."),
    ("purchase_confirm", "Can confirm a purchase order into warehouse stock (goods receipt)."),
    ("view_profit", "Can see cost of goods, gross profit and margin on orders and analytics."),
    ("print_labels", "Can print stock, roll and package labels."),
    ("manager", "Set on whoever lacks the Orders permission."),
    ("sales_rep", "Set on whoever lacks the Beyond sales permission."),
]


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0033_middle_manager_into_its_permissions"),
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
