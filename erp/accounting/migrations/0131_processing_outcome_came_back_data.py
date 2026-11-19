"""A roll that came back from the work is stored as "came_back", not
"returned": "returned" read like goods sent back to us as faulty."""
from django.db import migrations


def forwards(apps, schema_editor):
    apps.get_model("accounting", "ProcessingLine").objects \
        .filter(outcome="returned").update(outcome="came_back")


def backwards(apps, schema_editor):
    apps.get_model("accounting", "ProcessingLine").objects \
        .filter(outcome="came_back").update(outcome="returned")


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0130_processing_outcome_came_back_choice"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
