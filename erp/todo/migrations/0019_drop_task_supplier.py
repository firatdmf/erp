# The CRM Supplier record is retired (CR14, 2026-11-17); no task named one.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("todo", "0018_task_repeat"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="task",
            name="supplier",
        ),
    ]
