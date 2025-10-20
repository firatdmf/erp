from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from crm.models import CompanyFollowUp, Company
from crm.gmail_service import GmailReplyDetector
from todo.models import Task
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check Gmail for replies from prospect companies and stop follow-ups'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours-back',
            type=int,
            default=24,
            help='How many hours back to check for replies (default: 24)',
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Check only for a specific company ID (for testing)',
        )

    def handle(self, *args, **options):
        hours_back = options['hours_back']
        company_id = options.get('company_id')
        
        self.stdout.write(f'Checking for email replies from the last {hours_back} hours...')
        
        # Get all active follow-ups
        followups = CompanyFollowUp.objects.filter(is_active=True).select_related('company')
        
        if company_id:
            followups = followups.filter(company_id=company_id)
        
        if not followups.exists():
            self.stdout.write(self.style.WARNING('No active follow-ups to check'))
            return
        
        self.stdout.write(f'Checking {followups.count()} active follow-ups for replies...')
        
        # Initialize Gmail detector
        detector = GmailReplyDetector()
        if not detector.authenticate():
            self.stdout.write(
                self.style.ERROR(
                    'Failed to authenticate with Gmail API. '
                    'Run: python manage.py setup_gmail_api'
                )
            )
            return
        
        replies_found = 0
        tasks_created = 0
        
        for followup in followups:
            company = followup.company
            
            if not company.email:
                continue
            
            # Check for replies
            reply_info = detector.check_for_replies(
                company.email,
                hours_back=hours_back * 24  # Convert to hours for the service
            )
            
            if reply_info['has_reply']:
                replies_found += 1
                reply_date = reply_info['reply_date'] or timezone.now()
                snippet = reply_info['message_snippet'] or 'No preview available'
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Reply detected from {company.name} ({company.email})'
                    )
                )
                self.stdout.write(f'  Reply date: {reply_date}')
                self.stdout.write(f'  Preview: {snippet[:100]}...')
                
                # Stop follow-ups
                followup.stop_followups(reason='reply_received')
                self.stdout.write(f'  ✓ Stopped follow-ups for {company.name}')
                
                # Create a task to reply back
                try:
                    # Check if task already exists
                    existing_task = Task.objects.filter(
                        company=company,
                        name__icontains='Reply back',
                        completed=False
                    ).first()
                    
                    if not existing_task:
                        task = Task.objects.create(
                            name=f'Reply back to {company.name}',
                            description=f'Company replied on {reply_date.strftime("%Y-%m-%d %H:%M")}\n\n'
                                       f'Preview: {snippet[:200]}\n\n'
                                       f'Check email and reply to: {company.email}',
                            company=company,
                            due_date=(timezone.now() + timedelta(days=1)).date(),
                            completed=False
                        )
                        tasks_created += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Created task: "Reply back to {company.name}"'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ⚠ Task already exists for {company.name}'
                            )
                        )
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Failed to create task for {company.name}: {e}'
                        )
                    )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('='*50)
        self.stdout.write(f'Checked: {followups.count()} companies')
        self.stdout.write(f'Replies found: {replies_found}')
        self.stdout.write(f'Tasks created: {tasks_created}')
        self.stdout.write(f'Follow-ups stopped: {replies_found}')
        
        if replies_found > 0:
            self.stdout.write(
                '\n' + self.style.NOTICE(
                    '✉️  Check your todo list to see tasks for replying back!'
                )
            )
