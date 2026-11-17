# The CRM Supplier record is retired (CR14, 2026-11-17): its 12 rows became
# companies on production and were deleted. With every link to it gone
# (accounts, receipts, tasks, notes, files), the table goes too.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0027_company_status_optional"),
        ("accounting", "0126_drop_supplier_links"),
        ("operating", "0125_drop_supplier_links"),
        ("todo", "0019_drop_task_supplier"),
        # The procurement stub's models pointed at Supplier until its 0002
        # released them; on a fresh build that has to happen first.
        ("procurement", "0002_remove_purchaseorderitem_purchase_order_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="note",
            name="supplier",
        ),
        migrations.RemoveField(
            model_name="attachment",
            name="supplier",
        ),
        migrations.DeleteModel(
            name="Supplier",
        ),
    ]
