from django.core.management.base import BaseCommand
from email_automation.email_service import process_scheduled_campaigns


class Command(BaseCommand):
    help = 'Process and send all scheduled campaign emails'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Processing scheduled campaigns...'))
        
        sent_count = process_scheduled_campaigns()
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Successfully sent {sent_count} emails')
        )
