from django.db import migrations


def forward(apps, schema_editor):
    apps.get_model("operating", "OrderChange").objects.filter(
        field="order_status").update(field="status")


def backward(apps, schema_editor):
    apps.get_model("operating", "OrderChange").objects.filter(
        action="status", field="status").update(field="order_status")


class Migration(migrations.Migration):
    """The order's history names the status field by its new name."""

    dependencies = [
        ("operating", "0128_order_status_takes_the_name"),
    ]

    operations = [migrations.RunPython(forward, backward)]
