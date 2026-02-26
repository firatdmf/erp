# Manual migration to restore product_variant FK on ProductFile
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0057_alter_product_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='productfile',
            name='product_variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='files', to='marketing.productvariant'),
        ),
    ]
