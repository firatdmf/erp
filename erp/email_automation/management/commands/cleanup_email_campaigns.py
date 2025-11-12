from django.core.management.base import BaseCommand
from email_automation.models import EmailCampaign
from crm.models import Company
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup unwanted email campaigns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📧 EMAIL CAMPAIGN CLEANUP TOOL'))
        self.stdout.write('='*60 + '\n')
        
        # Get all campaigns
        campaigns = EmailCampaign.objects.select_related('company').all()
        
        total = campaigns.count()
        active = campaigns.filter(status='active').count()
        
        self.stdout.write(f'📊 Total campaigns: {total}')
        self.stdout.write(f'   ✅ Active: {active}')
        self.stdout.write(f'   ❌ Inactive: {total - active}\n')
        
        # Categorize
        to_delete = []
        to_review = []
        looks_good = []
        
        for campaign in campaigns:
            company = campaign.company
            
            # No email
            if not company.email or len(company.email) == 0:
                to_delete.append((campaign, 'NO_EMAIL', 'Company has no email'))
            
            # Not prospect
            elif company.status != 'prospect':
                to_delete.append((campaign, 'NOT_PROSPECT', f'Status: {company.status}'))
            
            # Inactive
            elif campaign.status != 'active':
                to_review.append((campaign, campaign.status.upper(), f'{campaign.emails_sent}/6 emails'))
            
            # Active and good
            else:
                looks_good.append((campaign, 'ACTIVE', f'{campaign.emails_sent}/6 emails'))
        
        # Display
        if to_delete:
            self.stdout.write(self.style.ERROR(f'\n❌ SHOULD BE DELETED ({len(to_delete)}):'))
            self.stdout.write('-' * 60)
            for campaign, code, reason in to_delete:
                self.stdout.write(f'  • {campaign.company.name:40} | {code:15} | {reason}')
        
        if to_review:
            self.stdout.write(self.style.WARNING(f'\n⚠️  FOR REVIEW ({len(to_review)}):'))
            self.stdout.write('-' * 60)
            for campaign, code, reason in to_review:
                self.stdout.write(f'  • {campaign.company.name:40} | {code:15} | {reason}')
        
        if looks_good:
            self.stdout.write(self.style.SUCCESS(f'\n✅ LOOKS GOOD ({len(looks_good)}):'))
            self.stdout.write('-' * 60)
            for campaign, code, reason in looks_good:
                self.stdout.write(f'  • {campaign.company.name:40} | {code:15} | {reason}')
        
        # Delete
        if to_delete:
            self.stdout.write('\n' + '='*60)
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'ℹ️  DRY RUN: Would delete {len(to_delete)} campaign(s)')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'🗑️  DELETING {len(to_delete)} campaign(s)...')
                )
                
                deleted = 0
                for campaign, code, reason in to_delete:
                    try:
                        name = campaign.company.name
                        campaign.delete()
                        deleted += 1
                        self.stdout.write(f'   ✓ Deleted: {name}')
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'   ✗ Failed: {name} - {str(e)}')
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f'\n✅ Deleted {deleted}/{len(to_delete)} campaigns')
                )
        else:
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('✨ No campaigns need deletion!'))
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📋 SUMMARY'))
        self.stdout.write('='*60)
        self.stdout.write(f'   To Delete:    {len(to_delete)}')
        self.stdout.write(f'   For Review:   {len(to_review)}')
        self.stdout.write(f'   Looks Good:   {len(looks_good)}')
        
        if dry_run and to_delete:
            self.stdout.write(
                self.style.NOTICE(f'\n💡 Run without --dry-run to delete {len(to_delete)} campaigns')
            )
        
        self.stdout.write('')
