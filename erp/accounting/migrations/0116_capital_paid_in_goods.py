from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operating', '0107_stockmovement_purpose_unpurchased'),
        ('accounting', '0115_book_directory'),
    ]

    operations = [
        migrations.AddField(
            model_name='equitycapital',
            name='paid_in',
            field=models.CharField(choices=[('cash', 'Cash'), ('goods', 'Goods')], default='cash', max_length=5),
        ),
        migrations.AddField(
            model_name='equitycapital',
            name='warehouse',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='capital_contributions', to='operating.warehouse'),
        ),
        migrations.AlterField(
            model_name='equitycapital',
            name='cash_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounting.cashaccount'),
        ),
    ]
