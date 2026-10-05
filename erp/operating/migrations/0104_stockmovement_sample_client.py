import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0001_initial"),
        ("operating", "0103_stockmovement_purpose_correction"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockmovement",
            name="contact",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="stock_movements", to="crm.contact",
                help_text="The contact a sample went to, when it went to a person."),
        ),
        migrations.AddField(
            model_name="stockmovement",
            name="company",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="stock_movements", to="crm.company",
                help_text="The company a sample went to, when it went to a company."),
        ),
    ]
