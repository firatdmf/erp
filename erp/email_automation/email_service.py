"""
Email sending service with template personalization
"""
from django.utils import timezone
from datetime import timedelta
from .models import EmailAccount, EmailTemplate, EmailCampaign, SentEmail
from .gmail_utils import get_gmail_service, send_email
import re


def replace_template_variables(text, context):
    """
    Replace template variables like {{company_name}} with actual values
    """
    if not text:
        return text
    
    # Replace all variables in the format {{variable_name}}
    for key, value in context.items():
        pattern = r'\{\{' + key + r'\}\}'
        text = re.sub(pattern, str(value or ''), text, flags=re.IGNORECASE)
    
    return text


def get_template_context(campaign, contact=None):
    """
    Build context dictionary for template variables
    """
    company = campaign.company
    user = campaign.user
    
    context = {
        'company_name': company.name,
        'user_name': f"{user.first_name} {user.last_name}".strip() or user.username,
        'user_company': getattr(user, 'member', None) and getattr(user.member, 'company_name', 'Our Company') or 'Our Company',
    }
    
    # Add contact info if available (email is ArrayField)
    if contact:
        # Get first email from array or use name
        first_email = contact.email[0] if contact.email and len(contact.email) > 0 else None
        context['contact_name'] = contact.name or first_email or 'there'
    elif company.contacts.exists():
        first_contact = company.contacts.first()
        first_email = first_contact.email[0] if first_contact.email and len(first_contact.email) > 0 else None
        context['contact_name'] = first_contact.name or first_email or 'there'
    else:
        context['contact_name'] = 'there'
    
    # Add user title if available
    if hasattr(user, 'member') and hasattr(user.member, 'title'):
        context['user_title'] = user.member.title
    else:
        context['user_title'] = 'Sales Team'
    
    return context


def send_campaign_email(campaign, sequence_number):
    """
    Send a specific email in the campaign sequence
    """
    # Get email account
    try:
        email_account = EmailAccount.objects.get(user=campaign.user)
    except EmailAccount.DoesNotExist:
        print(f"✗ No email account for user {campaign.user.username}")
        return False
    
    # Get template
    try:
        template = EmailTemplate.objects.get(
            user=campaign.user,
            sequence_number=sequence_number,
            is_active=True
        )
    except EmailTemplate.DoesNotExist:
        print(f"✗ No template found for sequence {sequence_number}")
        return False
    
    # Determine recipient
    company = campaign.company
    recipient_email = None
    recipient_name = ''
    
    # Try to get email from contacts first (email is ArrayField)
    if company.contacts.exists():
        # Find contacts with at least one email in their array
        for contact in company.contacts.all():
            if contact.email and len(contact.email) > 0 and contact.email[0].strip():
                recipient_email = contact.email[0]  # Take first email from array
                recipient_name = contact.name or recipient_email
                break
    
    # Fallback to company email (array - take first email)
    if not recipient_email and company.email and len(company.email) > 0:
        recipient_email = company.email[0]  # Take first email from array
        recipient_name = company.name
    
    if not recipient_email:
        print(f"✗ No email address found for {company.name}")
        return False
    
    # Build template context
    context = get_template_context(campaign)
    
    # Replace variables in subject and body
    subject = replace_template_variables(template.subject, context)
    body = replace_template_variables(template.body, context)
    
    # Send email via Gmail
    try:
        service = get_gmail_service(email_account)
        sent_message = send_email(
            service=service,
            sender=email_account.email_address,
            to=recipient_email,
            subject=subject,
            message_text=body,
            html_body=body.replace('\n', '<br>')  # Simple HTML conversion
        )
        
        if sent_message:
            # Record sent email
            sent_email = SentEmail.objects.create(
                campaign=campaign,
                template=template,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                body=body,
                gmail_message_id=sent_message.get('id', ''),
                gmail_thread_id=sent_message.get('threadId', '')
            )
            
            # Update campaign
            campaign.emails_sent += 1
            campaign.last_email_sent_at = timezone.now()
            
            # Schedule next email if not at max
            if campaign.emails_sent < 6:
                next_sequence = campaign.emails_sent + 1
                try:
                    next_template = EmailTemplate.objects.get(
                        user=campaign.user,
                        sequence_number=next_sequence,
                        is_active=True
                    )
                    # Calculate delay based on unit
                    delay_kwargs = {}
                    if next_template.delay_unit == 'minutes':
                        delay_kwargs['minutes'] = next_template.delay_amount
                    elif next_template.delay_unit == 'hours':
                        delay_kwargs['hours'] = next_template.delay_amount
                    else:  # days
                        delay_kwargs['days'] = next_template.delay_amount
                    
                    campaign.next_email_scheduled_at = timezone.now() + timedelta(**delay_kwargs)
                    print(f"  Next email ({next_sequence}) scheduled for {campaign.next_email_scheduled_at}")
                except EmailTemplate.DoesNotExist:
                    # No template for next email yet - keep campaign active but unscheduled
                    # User can add templates later
                    campaign.next_email_scheduled_at = None
                    print(f"  No template found for email {next_sequence} - campaign remains active")
            else:
                # All 6 emails sent
                campaign.status = 'completed'
                campaign.next_email_scheduled_at = None
                print(f"  All 6 emails sent - campaign completed")
            
            campaign.save()
            
            print(f"✓ Email {sequence_number} sent to {recipient_email} for campaign {campaign.id}")
            return True
        else:
            print(f"✗ Failed to send email")
            return False
            
    except Exception as e:
        print(f"✗ Error sending email: {str(e)}")
        return False


def process_scheduled_campaigns():
    """
    Process all campaigns that have emails scheduled to be sent
    """
    now = timezone.now()
    
    # Get campaigns ready to send - must have company email or contact with email
    campaigns = EmailCampaign.objects.filter(
        status='active',
        next_email_scheduled_at__lte=now,
        emails_sent__lt=6
    ).select_related('company', 'user')
    
    sent_count = 0
    for campaign in campaigns:
        # Skip if company has no email (check if array is empty)
        if not campaign.company.email or len(campaign.company.email) == 0:
            # Check if company has contacts with email (email is ArrayField)
            has_contact_email = False
            for contact in campaign.company.contacts.all():
                if contact.email and len(contact.email) > 0 and contact.email[0].strip():
                    has_contact_email = True
                    break
            
            if not has_contact_email:
                print(f"⊘ Skipping campaign {campaign.id} - no email address for {campaign.company.name}")
                # Pause this campaign
                campaign.status = 'paused'
                campaign.save()
                continue
        
        sequence_number = campaign.emails_sent + 1
        if send_campaign_email(campaign, sequence_number):
            sent_count += 1
    
    print(f"✓ Processed {campaigns.count()} campaigns, sent {sent_count} emails")
    return sent_count
