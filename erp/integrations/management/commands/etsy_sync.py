from django.core.management.base import BaseCommand

from integrations.etsy_sync import sync
from integrations.models import EtsyConnection


class Command(BaseCommand):
    help = "Record what every switched-on Etsy shop did since its last sync."

    def handle(self, *args, **options):
        for connection in EtsyConnection.objects.filter(sync_from__isnull=False):
            recorded, waiting = sync(connection)
            self.stdout.write(f"{connection}: {recorded} recorded, {waiting} waiting for a person")
