from django.core.management.base import BaseCommand
from django.utils import timezone
from crm.models import CompanyFollowUp
from crm.email_utils import send_followup_email
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send scheduled follow-up emails to prospect companies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails',
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Send follow-up only for a specific company ID (for testing)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        company_id = options.get('company_id')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no emails will be sent'))
        
        # Get all active follow-ups
        followups = CompanyFollowUp.objects.filter(is_active=True).select_related('company')
        
        if company_id:
            followups = followups.filter(company_id=company_id)
        
        if not followups.exists():
            self.stdout.write(self.style.WARNING('No active follow-ups found'))
            return
        
        self.stdout.write(f'Checking {followups.count()} active follow-ups...')
        
        emails_sent = 0
        emails_failed = 0
        max_emails_reached = []
        
        for followup in followups:
            company = followup.company
            
            # Check if company status is still 'prospect'
            if company.status != 'prospect':
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipping {company.name}: Status changed to {company.status}'
                    )
                )
                followup.stop_followups(reason='status_changed')
                continue
            
            # Check if email should be sent
            should_send, days_to_wait = followup.should_send_email()
            
            if not should_send:
                if followup.emails_sent_count >= 5:
                    if followup.is_active:
                        # Mark as completed
                        followup.stop_followups(reason='max_emails_reached')
                        max_emails_reached.append(company.name)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Completed follow-up sequence for {company.name} (5/5 emails sent)'
                            )
                        )
                continue
            
            # Calculate which email to send (1-5)
            email_number = followup.emails_sent_count + 1
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[DRY RUN] Would send email {email_number}/5 to {company.name} ({company.email})'
                    )
                )
            else:
                self.stdout.write(f'Sending email {email_number}/5 to {company.name} ({company.email})...')
                
                # Send the email
                success = send_followup_email(company, email_number)
                
                if success:
                    # Mark email as sent
                    followup.mark_email_sent()
                    emails_sent += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Sent email {email_number}/5 to {company.name}'
                        )
                    )
                    
                    # Check if this was the last email
                    if email_number == 5:
                        max_emails_reached.append(company.name)
                else:
                    emails_failed += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ Failed to send email to {company.name}'
                        )
                    )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('='*50)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('This was a DRY RUN - no emails were actually sent'))
        else:
            self.stdout.write(f'Emails sent successfully: {emails_sent}')
            self.stdout.write(f'Emails failed: {emails_failed}')
        
        if max_emails_reached:
            self.stdout.write('\n' + self.style.WARNING('FOLLOW-UP SEQUENCES COMPLETED:'))
            for company_name in max_emails_reached:
                self.stdout.write(f'  - {company_name} (reached 5/5 emails)')
            self.stdout.write(
                self.style.NOTICE(
                    f'\n⚠️  {len(max_emails_reached)} compan{"y" if len(max_emails_reached) == 1 else "ies"} '
                    f'reached the maximum follow-up limit. Consider manual outreach.'
                )
            )
