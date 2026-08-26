from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Install `unaccent` so searches can fold Turkish letters.

    The `erp` app has no models; this migration exists only to make the
    extension part of the schema history instead of a manual step on
    each database. See erp/search_utils.py for the query side.
    """

    initial = True

    dependencies = []

    operations = [
        UnaccentExtension(),
    ]
