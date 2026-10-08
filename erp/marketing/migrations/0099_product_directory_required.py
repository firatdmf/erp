from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    # Apart from 0098 on purpose: Postgres will not alter a table the same
    # transaction has just rewritten rows of.
    dependencies = [
        ('marketing', '0098_file_products_with_their_business'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='directory',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='crm.directory'),
        ),
    ]
