import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("operating", "0104_stockmovement_sample_client"),
    ]

    operations = [
        migrations.CreateModel(
            name="SamplePackage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ("note", models.CharField(blank=True, default="", max_length=255)),
                ("status", models.CharField(
                    choices=[("prepared", "Prepared"), ("sent", "Sent"), ("delivered", "Delivered")],
                    default="prepared", max_length=16)),
                ("carrier", models.CharField(blank=True, default="", max_length=50)),
                ("tracking_number", models.CharField(blank=True, default="", max_length=100)),
                ("shipped_at", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="sample_packages", to="crm.company")),
                ("contact", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="sample_packages", to="crm.contact")),
                ("created_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="sample_packages", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
        migrations.AddField(
            model_name="stockmovement",
            name="sample_package",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="movements", to="operating.samplepackage",
                help_text="The sample package this cut went out in, when it went in one."),
        ),
    ]
