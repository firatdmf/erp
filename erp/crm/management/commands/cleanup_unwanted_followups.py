from django.core.management.base import BaseCommand
from crm.models import CompanyFollowUp
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup follow-up records for companies that should not be in email automation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--inactive-only',
            action='store_true',
            help='Only show/delete inactive follow-ups',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        inactive_only = options['inactive_only']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📧 FOLLOW-UP CLEANUP TOOL'))
        self.stdout.write('='*60 + '\n')
        
        # Get all follow-ups
        followups = CompanyFollowUp.objects.select_related('company').all()
        
        if inactive_only:
            followups = followups.filter(is_active=False)
            self.stdout.write(f'📊 Total inactive follow-ups: {followups.count()}\n')
        else:
            active_count = followups.filter(is_active=True).count()
            inactive_count = followups.filter(is_active=False).count()
            self.stdout.write(f'📊 Total follow-ups: {followups.count()}')
            self.stdout.write(f'   ✅ Active: {active_count}')
            self.stdout.write(f'   ❌ Inactive: {inactive_count}\n')
        
        # Categorize follow-ups
        to_delete = []
        to_review = []
        looks_good = []
        
        for followup in followups:
            company = followup.company
            
            # Category 1: Company has no email (can't send anyway)
            if not company.email:
                to_delete.append((followup, 'NO_EMAIL', 'Company has no email address'))
            
            # Category 2: Company status is not prospect
            elif company.status != 'prospect':
                to_delete.append((followup, 'NOT_PROSPECT', f'Status is "{company.status}"'))
            
            # Category 3: Already inactive (completed/stopped)
            elif not followup.is_active:
                if followup.stopped_reason == 'max_emails_reached':
                    to_review.append((followup, 'COMPLETED', f'Completed sequence ({followup.emails_sent_count}/5 emails)'))
                else:
                    to_review.append((followup, 'STOPPED', f'Stopped: {followup.stopped_reason}'))
            
            # Category 4: Active and looks good
            else:
                looks_good.append((followup, 'ACTIVE', f'Active - {followup.emails_sent_count}/5 emails sent'))
        
        # Display results
        if to_delete:
            self.stdout.write(self.style.ERROR(f'\n❌ SHOULD BE DELETED ({len(to_delete)}):'))
            self.stdout.write('-' * 60)
            for followup, reason_code, reason_text in to_delete:
                self.stdout.write(
                    f'  • {followup.company.name:40} | {reason_code:15} | {reason_text}'
                )
        
        if to_review:
            self.stdout.write(self.style.WARNING(f'\n⚠️  FOR REVIEW ({len(to_review)}):'))
            self.stdout.write('-' * 60)
            for followup, reason_code, reason_text in to_review:
                self.stdout.write(
                    f'  • {followup.company.name:40} | {reason_code:15} | {reason_text}'
                )
        
        if looks_good:
            self.stdout.write(self.style.SUCCESS(f'\n✅ LOOKS GOOD ({len(looks_good)}):'))
            self.stdout.write('-' * 60)
            for followup, reason_code, reason_text in looks_good:
                self.stdout.write(
                    f'  • {followup.company.name:40} | {reason_code:15} | {reason_text}'
                )
        
        # Delete action
        if to_delete:
            self.stdout.write('\n' + '='*60)
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'ℹ️  DRY RUN: Would delete {len(to_delete)} follow-up record(s)'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'🗑️  DELETING {len(to_delete)} follow-up record(s)...'
                    )
                )
                
                deleted_count = 0
                for followup, reason_code, reason_text in to_delete:
                    try:
                        company_name = followup.company.name
                        followup.delete()
                        deleted_count += 1
                        self.stdout.write(f'   ✓ Deleted: {company_name}')
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'   ✗ Failed to delete {company_name}: {str(e)}')
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f'\n✅ Successfully deleted {deleted_count}/{len(to_delete)} records')
                )
        else:
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('✨ No follow-ups need to be deleted!'))
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📋 SUMMARY'))
        self.stdout.write('='*60)
        self.stdout.write(f'   To Delete:    {len(to_delete)} records')
        self.stdout.write(f'   For Review:   {len(to_review)} records')
        self.stdout.write(f'   Looks Good:   {len(looks_good)} records')
        
        if dry_run and to_delete:
            self.stdout.write(
                self.style.NOTICE(
                    f'\n💡 TIP: Run without --dry-run to actually delete {len(to_delete)} records'
                )
            )
        
        self.stdout.write('')
