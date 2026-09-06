from django.db import migrations


class Migration(migrations.Migration):
    """Release the purchasing models — state only.

    operating/0076 renamed the physical tables and took ownership of them.
    These deletions must therefore touch state ONLY; letting them reach the
    database would drop the tables that migration just adopted.

    The app itself stays installed as a migrations-only stub so the graph keeps
    resolving on databases that already applied 0001.
    """

    dependencies = [
        ('procurement', '0001_initial'),
        # operating must adopt the tables before this releases the state,
        # otherwise a fresh build has nothing to rename.
        ('operating', '0076_adopt_purchasing_from_procurement'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='purchaseorderitem',
                    name='purchase_order',
                ),
                migrations.RemoveField(
                    model_name='purchaseorderitem',
                    name='request_item',
                ),
                migrations.RemoveField(
                    model_name='purchaserequest',
                    name='approved_by',
                ),
                migrations.RemoveField(
                    model_name='purchaserequest',
                    name='requester',
                ),
                migrations.RemoveField(
                    model_name='purchaserequestitem',
                    name='product',
                ),
                migrations.RemoveField(
                    model_name='purchaserequestitem',
                    name='raw_material',
                ),
                migrations.RemoveField(
                    model_name='purchaserequestitem',
                    name='request',
                ),
                migrations.RemoveField(
                    model_name='requestforquotation',
                    name='created_by',
                ),
                migrations.RemoveField(
                    model_name='requestforquotation',
                    name='requests',
                ),
                migrations.RemoveField(
                    model_name='requestforquotation',
                    name='suppliers',
                ),
                migrations.DeleteModel(
                    name='PurchaseOrder',
                ),
                migrations.DeleteModel(
                    name='PurchaseOrderItem',
                ),
                migrations.DeleteModel(
                    name='PurchaseRequest',
                ),
                migrations.DeleteModel(
                    name='PurchaseRequestItem',
                ),
                migrations.DeleteModel(
                    name='RequestForQuotation',
                ),
            ],
            database_operations=[],
        ),
    ]
