from django.db import migrations, models
import django.db.models.deletion


def clear_combined_books(apps, schema_editor):
    # A combined warehouse owns no stock, so it names no book — its
    # members each carry their own.
    Warehouse = apps.get_model("operating", "Warehouse")
    Warehouse.objects.filter(kind="combined").update(accounting_book=None)


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0001_initial'),
        ('operating', '0093_drop_order_print_header'),
    ]

    operations = [
        migrations.AlterField(
            model_name='warehouse',
            name='accounting_book',
            field=models.ForeignKey(blank=True, help_text="Accounting book this warehouse's stock belongs to (normal warehouses only)", null=True, on_delete=django.db.models.deletion.PROTECT, related_name='warehouses', to='accounting.book'),
        ),
        migrations.RunPython(clear_combined_books, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='warehouse',
            constraint=models.CheckConstraint(check=models.Q(models.Q(('accounting_book__isnull', False), ('kind', 'normal')), models.Q(('accounting_book__isnull', True), ('kind', 'combined')), _connector='OR'), name='warehouse_book_only_on_normal'),
        ),
    ]
