# The CRM Supplier record is retired (CR14, 2026-11-17). The raw-material
# receipts, requests for quotation and procurement purchase orders that
# named one are all empty tables.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0124_unit_cost_base_required"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="rawmaterialgoodreceipt",
            name="unique_supplier_receipt_number",
        ),
        migrations.RemoveField(
            model_name="rawmaterialgoodreceipt",
            name="supplier",
        ),
        migrations.RemoveField(
            model_name="requestforquotation",
            name="suppliers",
        ),
        migrations.RemoveField(
            model_name="purchaseorder",
            name="supplier",
        ),
    ]
