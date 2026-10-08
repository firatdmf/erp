from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    # Columns only. The rows are filed in 0098, apart from this on purpose:
    # Postgres will not build the new column's index in a transaction that
    # has just rewritten the table's rows ("pending trigger events").

    dependencies = [
        ('crm', '0026_unique_names_per_directory'),
        ('accounting', '0115_book_directory'),
        ('operating', '0107_stockmovement_purpose_unpurchased'),
        ('marketing', '0096_supplier_sku_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='directory',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='crm.directory'),
        ),
        migrations.AddField(
            model_name='product',
            name='shared_with',
            field=models.ManyToManyField(blank=True, editable=False, related_name='shared_products', to='crm.directory'),
        ),
    ]
