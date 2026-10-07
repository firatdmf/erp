from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0094_english_field_labels'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='pack_type',
            field=models.CharField(choices=[('roll', 'Roll'), ('box', 'Box'), ('bale', 'Bale'), ('bag', 'Bag'), ('bundle', 'Bundle'), ('pallet', 'Pallet'), ('loose', 'Loose')], default='roll', help_text='What one stock item of this product physically is', max_length=12),
        ),
    ]
