from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.db import models
from datetime import timedelta
from .models import EmailAccount, EmailTemplate, EmailCampaign, SentEmail, ReceivedEmail
from crm.models import Company
from authentication.models import GoogleChatCredentials
import json
from django.http import HttpResponse, HttpResponseForbidden, Http404
from . import gmail_utils

from django.http import HttpResponse, HttpResponseForbidden
from . import gmail_utils



@login_required
def dashboard(request):
    """Main email dashboard - shows Gmail connection status and campaigns"""
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        is_connected = True
    except EmailAccount.DoesNotExist:
        email_account = None
        is_connected = False
    
    # Get campaign statistics
    campaigns = EmailCampaign.objects.filter(user=request.user)
    active_campaigns = campaigns.filter(status='active').count()
    
    # Calculate today's statistics
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    total_sent = SentEmail.objects.filter(
        campaign__user=request.user,
        sent_at__range=(today_start, today_end)
    ).count()
    
    total_replies = ReceivedEmail.objects.filter(
        received_at__range=(today_start, today_end)
    ).count()
    
    # Calculate this week's conversions (companies changed from prospect to qualified)
    week_ago = timezone.now() - timedelta(days=7)
    conversions = campaigns.filter(
        status='completed',
        company__status='qualified',
        updated_at__gte=week_ago
    ).count()
    
    # Total qualified companies (all time)
    qualified_companies = Company.objects.filter(status='qualified').count()
    
    # Get recent campaigns
    recent_campaigns = campaigns.select_related('company').order_by('-created_at')[:10]
    
    context = {
        'email_account': email_account,
        'is_connected': is_connected,
        'active_campaigns': active_campaigns,
        'total_sent': total_sent,
        'total_replies': total_replies,
        'conversions': conversions,
        'qualified_companies': qualified_companies,
        'recent_campaigns': recent_campaigns,
    }
    
    return render(request, 'email_automation/dashboard.html', context)


@login_required
def connect_gmail(request):
    """Start Gmail OAuth flow"""
    from .gmail_utils import get_authorization_url
    
    # Check if already connected
    if EmailAccount.objects.filter(user=request.user).exists():
        messages.info(request, 'You already have a connected Gmail account.')
        return redirect('email_automation:dashboard')
    
    # Check if OAuth credentials are configured
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_CLIENT_SECRET:
        messages.error(request, 'Gmail OAuth is not configured. Please add GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET to your .env file.')
        return redirect('email_automation:dashboard')
    
    try:
        # Generate OAuth URL and redirect user
        authorization_url = get_authorization_url(request)
        return HttpResponseRedirect(authorization_url)
    except Exception as e:
        messages.error(request, f'Error starting OAuth flow: {str(e)}')
        return redirect('email_automation:dashboard')


@login_required
def oauth2callback(request):
    """Handle OAuth2 callback from Gmail"""
    from .gmail_utils import exchange_code_for_tokens, get_gmail_service, get_user_email
    
    # Get authorization code from query parameters
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    
    # Check for errors
    if error:
        messages.error(request, f'OAuth error: {error}')
        return redirect('email_automation:dashboard')
    
    if not code:
        messages.error(request, 'No authorization code received')
        return redirect('email_automation:dashboard')
    
    try:
        print(f"DEBUG: OAuth callback - code received: {code[:20]}...")
        print(f"DEBUG: OAuth callback - state: {state}")
        
        # Exchange code for tokens
        token_data = exchange_code_for_tokens(request, code, state)
        print(f"DEBUG: Token exchange successful")
        
        # Create credentials dict for getting email address
        creds_dict = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'token_uri': token_data['token_uri'],
            'client_id': token_data['client_id'],
            'client_secret': token_data['client_secret'],
            'scopes': token_data['scopes'],
        }
        
        # Create temporary email account object to get service
        temp_account = EmailAccount(
            user=request.user,
            access_token=token_data['access_token'],
            refresh_token=token_data['refresh_token']
        )
        
        # Get Gmail service and user email
        print(f"DEBUG: Getting Gmail service...")
        service = get_gmail_service(temp_account)
        print(f"DEBUG: Getting user email...")
        email_address = get_user_email(service)
        print(f"DEBUG: Email address retrieved: {email_address}")
        
        if not email_address:
            messages.error(request, 'Could not retrieve email address from Gmail')
            print("ERROR: Could not retrieve email address")
            return redirect('email_automation:dashboard')
        
        # Save email account
        print(f"DEBUG: Saving EmailAccount for user {request.user.username}...")
        email_account, created = EmailAccount.objects.update_or_create(
            user=request.user,
            defaults={
                'email_address': email_address,
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token'],
            }
        )
        
        action = 'connected' if created else 'reconnected'
        print(f"DEBUG: EmailAccount {'created' if created else 'updated'} successfully!")
        print(f"DEBUG: Saved email: {email_account.email_address}")
        messages.success(request, f'Successfully {action} Gmail account: {email_address}')
        
        # Clear OAuth state from session
        if 'oauth_state' in request.session:
            del request.session['oauth_state']
        
    except ValueError as e:
        print(f"ERROR: Security error - {str(e)}")
        messages.error(request, f'Security error: {str(e)}')
    except Exception as e:
        print(f"ERROR: Exception - {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error connecting Gmail: {str(e)}')
    
    return redirect('email_automation:dashboard')


@login_required
def disconnect_gmail(request):
    """Disconnect Gmail account"""
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        email_address = email_account.email_address
        email_account.delete()
        messages.success(request, f'Successfully disconnected {email_address}')
    except EmailAccount.DoesNotExist:
        messages.error(request, 'No Gmail account connected')
    
    return redirect('email_automation:dashboard')


@login_required
def inbox_view(request):
    """Show received emails - Only replies from companies we've sent campaigns to"""
    from .gmail_utils import get_gmail_service, list_messages, get_message, parse_message
    from datetime import datetime
    
    emails = []
    
    # Get all campaign recipient emails (companies we've sent emails to)
    sent_emails = SentEmail.objects.filter(
        campaign__user=request.user
    ).values_list('recipient_email', flat=True).distinct()
    
    recipient_emails_set = set(sent_emails)
    
    # Check if user has connected Gmail
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        
        # Get Gmail service
        service = get_gmail_service(email_account)
        
        # List recent messages
        message_list = list_messages(service, max_results=100)
        
        # Fetch and parse each message
        for msg_ref in message_list:
            msg = get_message(service, msg_ref['id'])
            if msg:
                parsed = parse_message(msg)
                
                # Extract sender email from parsed data
                sender_email = parsed.get('sender', '')
                # Try to extract email address from "Name <email@domain.com>" format
                if '<' in sender_email and '>' in sender_email:
                    sender_email = sender_email.split('<')[1].split('>')[0].strip()
                
                # Only include emails from recipients we've sent campaigns to
                if sender_email.lower() in [e.lower() for e in recipient_emails_set]:
                    # Convert to ReceivedEmail-like object for template
                    class EmailObject:
                        def __init__(self, data):
                            self.sender = data['sender']
                            self.subject = data['subject']
                            self.snippet = data['snippet']
                            self.received_at = datetime.now()  # Gmail doesn't return exact timestamp easily
                            self.body = data['body']
                    
                    emails.append(EmailObject(parsed))
    
    except EmailAccount.DoesNotExist:
        messages.warning(request, 'Please connect your Gmail account first to view emails.')
    except Exception as e:
        messages.error(request, f'Error fetching emails: {str(e)}')
    
    # Convert emails to JSON-serializable format
    emails_json = []
    for email in emails:
        emails_json.append({
            'sender': email.sender,
            'subject': email.subject,
            'snippet': email.snippet,
            'body': email.body,
            'received_at': email.received_at.isoformat() if hasattr(email.received_at, 'isoformat') else str(email.received_at),
        })
    
    context = {
        'emails': emails,
        'emails_json': json.dumps(emails_json),
        'page_title': 'Inbox',
    }
    
    return render(request, 'email_automation/inbox.html', context)


@login_required
def outbox_view(request):
    """Show sent emails"""
    sent_emails = SentEmail.objects.filter(
        campaign__user=request.user
    ).select_related('campaign', 'campaign__company').order_by('-sent_at')[:50]
    
    context = {
        'emails': sent_emails,
        'page_title': 'Outbox',
    }
    
    return render(request, 'email_automation/outbox.html', context)


@login_required
def template_list(request):
    """List all email templates"""
    templates = EmailTemplate.objects.filter(user=request.user).order_by('sequence_number')
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'email_automation/template_list.html', context)


@login_required
def template_create(request):
    """Create new email template"""
    from .forms import EmailTemplateForm
    
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, user=request.user)
        if form.is_valid():
            template = form.save()
            messages.success(request, f'Template "{template.name}" created successfully!')
            return redirect('email_automation:template_list')
    else:
        form = EmailTemplateForm(user=request.user)
    
    context = {
        'form': form,
        'page_title': 'Create Email Template',
        'button_text': 'Create Template',
    }
    
    return render(request, 'email_automation/template_form.html', context)


@login_required
def template_edit(request, pk):
    """Edit email template"""
    from .forms import EmailTemplateForm
    
    template = get_object_or_404(EmailTemplate, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template, user=request.user)
        if form.is_valid():
            template = form.save()
            messages.success(request, f'Template "{template.name}" updated successfully!')
            return redirect('email_automation:template_list')
    else:
        form = EmailTemplateForm(instance=template, user=request.user)
    
    context = {
        'form': form,
        'template': template,
        'page_title': f'Edit Template: {template.name}',
        'button_text': 'Update Template',
    }
    
    return render(request, 'email_automation/template_form.html', context)


@login_required
def campaign_list(request):
    """List all email campaigns"""
    campaigns = EmailCampaign.objects.filter(
        user=request.user
    ).select_related('company').order_by('-created_at')
    
    context = {
        'campaigns': campaigns,
    }
    
    return render(request, 'email_automation/campaign_list.html', context)


@login_required
def campaign_detail(request, pk):
    """Show campaign details"""
    campaign = get_object_or_404(EmailCampaign, pk=pk, user=request.user)
    sent_emails = campaign.sent_emails.all().order_by('-sent_at')
    
    context = {
        'campaign': campaign,
        'sent_emails': sent_emails,
    }
    
    return render(request, 'email_automation/campaign_detail.html', context)


@login_required
def api_inbox(request):
    """API endpoint to get inbox emails (replies)"""
    from .gmail_utils import get_gmail_service, list_messages, get_message, parse_message
    
    emails = []
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        service = get_gmail_service(email_account)
        message_list = list_messages(service, max_results=50)
        
        for msg_ref in message_list:
            msg = get_message(service, msg_ref['id'])
            if msg:
                parsed = parse_message(msg)
                emails.append({
                    'id': msg_ref['id'],
                    'sender': parsed['sender'],
                    'subject': parsed['subject'],
                    'snippet': parsed['snippet'],
                    'date': parsed.get('date', timezone.now().isoformat()),
                    'is_read': False,  # Gmail doesn't provide this easily
                })
    except Exception as e:
        print(f"Error fetching inbox: {str(e)}")
    
    return JsonResponse(emails, safe=False)


@login_required
def api_inbox_detail(request, message_id):
    """API endpoint to get single inbox email details"""
    from .gmail_utils import get_gmail_service, get_message, parse_message
    
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        service = get_gmail_service(email_account)
        msg = get_message(service, message_id)
        
        if msg:
            parsed = parse_message(msg)
            data = {
                'id': message_id,
                'sender': parsed['sender'],
                'subject': parsed['subject'],
                'body': parsed['body'],
                'date': parsed.get('date', timezone.now().isoformat()),
            }
            return JsonResponse(data)
    except Exception as e:
        print(f"Error fetching message: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Message not found'}, status=404)


@login_required
def api_sent(request):
    """API endpoint to get sent emails with date filter"""
    filter_type = request.GET.get('filter', 'all')
    
    sent_emails = SentEmail.objects.filter(
        campaign__user=request.user
    ).select_related('campaign', 'campaign__company', 'template')
    
    # Apply date filter
    if filter_type == 'today':
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        sent_emails = sent_emails.filter(sent_at__range=(today_start, today_end))
    elif filter_type == 'week':
        week_ago = timezone.now() - timedelta(days=7)
        sent_emails = sent_emails.filter(sent_at__gte=week_ago)
    elif filter_type == 'month':
        month_ago = timezone.now() - timedelta(days=30)
        sent_emails = sent_emails.filter(sent_at__gte=month_ago)
    
    sent_emails = sent_emails.order_by('-sent_at')[:100]
    
    data = [{
        'id': email.id,
        'recipient': email.recipient_name or email.recipient_email,
        'subject': email.subject,
        'date': email.sent_at.isoformat(),
        'company_name': email.campaign.company.name if email.campaign.company else '',
    } for email in sent_emails]
    
    return JsonResponse(data, safe=False)


@login_required
def api_sent_detail(request, pk):
    """API endpoint to get sent email details"""
    sent_email = get_object_or_404(
        SentEmail, 
        pk=pk, 
        campaign__user=request.user
    )
    
    data = {
        'id': sent_email.id,
        'subject': sent_email.subject,
        'body': sent_email.body,
        'recipient': sent_email.recipient_name or sent_email.recipient_email,
        'to_email': sent_email.recipient_email,
        'from_email': sent_email.campaign.user.emailaccount.email_address if hasattr(sent_email.campaign.user, 'emailaccount') else '',
        'date': sent_email.sent_at.isoformat(),
        'replied': sent_email.replied,
        'company_name': sent_email.campaign.company.name if sent_email.campaign.company else '',
        'template_name': sent_email.template.name if sent_email.template else '',
        'sequence_number': sent_email.template.sequence_number if sent_email.template else None,
    }
    
    return JsonResponse(data)


@login_required
def api_templates(request):
    """API endpoint to get email templates"""
    templates = EmailTemplate.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('sequence_number')
    
    data = [{
        'id': template.id,
        'name': template.name,
        'subject': template.subject,
        'sequence_number': template.sequence_number,
        'delay_days': template.delay_amount if template.delay_unit == 'days' else template.days_after_previous,
    } for template in templates]
    
    return JsonResponse(data, safe=False)


@login_required
def api_campaigns(request):
    """API endpoint to get campaigns"""
    campaigns = EmailCampaign.objects.filter(
        user=request.user
    ).select_related('company').order_by('-created_at')[:50]
    
    data = [{
        'id': campaign.id,
        'company_name': campaign.company.name,
        'status': campaign.status,
        'sent_count': campaign.emails_sent,
        'reply_count': 1 if campaign.reply_received else 0,
    } for campaign in campaigns]
    
    return JsonResponse(data, safe=False)


@login_required
def sent_email_detail_api(request, pk):
    """API endpoint to get sent email details (legacy)"""
    sent_email = get_object_or_404(
        SentEmail, 
        pk=pk, 
        campaign__user=request.user
    )
    
    data = {
        'id': sent_email.id,
        'subject': sent_email.subject,
        'body': sent_email.body,
        'recipient_email': sent_email.recipient_email,
        'recipient_name': sent_email.recipient_name or '',
        'sent_at': sent_email.sent_at.strftime('%b %d, %Y at %H:%M'),
        'replied': sent_email.replied,
        'company_name': sent_email.campaign.company.name if sent_email.campaign.company else '',
        'template_name': sent_email.template.name if sent_email.template else '',
        'sequence_number': sent_email.template.sequence_number if sent_email.template else None,
    }
    
    return JsonResponse(data)


@login_required
def campaign_pause(request, pk):
    """Pause an active campaign"""
    campaign = get_object_or_404(EmailCampaign, pk=pk, user=request.user)
    
    if campaign.status == 'active':
        campaign.status = 'paused'
        campaign.save()
        messages.success(request, f'Campaign for {campaign.company.name} has been paused.')
    else:
        messages.info(request, f'Campaign is already {campaign.status}.')
    
    return redirect('email_automation:campaign_detail', pk=campaign.pk)


@login_required
def campaign_resume(request, pk):
    """Resume a paused campaign"""
    campaign = get_object_or_404(EmailCampaign, pk=pk, user=request.user)
    
    if campaign.status == 'paused':
        campaign.status = 'active'
        
        # If no next email scheduled, schedule the next one
        if not campaign.next_email_scheduled_at and campaign.emails_sent < 6:
            next_sequence = campaign.emails_sent + 1
            try:
                next_template = EmailTemplate.objects.get(
                    user=request.user,
                    sequence_number=next_sequence,
                    is_active=True
                )
                # Schedule immediately or with a small delay
                campaign.next_email_scheduled_at = timezone.now()
            except EmailTemplate.DoesNotExist:
                pass
        
        campaign.save()
        messages.success(request, f'Campaign for {campaign.company.name} has been resumed.')
    else:
        messages.info(request, f'Campaign is currently {campaign.status}.')
    
    return redirect('email_automation:campaign_detail', pk=campaign.pk)


@login_required
def campaign_delete(request, pk):
    """Delete a campaign"""
    campaign = get_object_or_404(EmailCampaign, pk=pk, user=request.user)
    company_name = campaign.company.name
    
    if request.method == 'POST':
        campaign.delete()
        messages.success(request, f'Campaign for {company_name} has been deleted.')
        return redirect('email_automation:campaign_list')
    
    # If GET request, redirect back
    return redirect('email_automation:campaign_detail', pk=campaign.pk)


# ============================================================
# MY EMAILS - Personal email management views
# ============================================================
from .models import Email, EmailAttachment
from crm.models import Contact


@login_required
def my_emails(request):
    """
    Main user email dashboard.
    Handles 'inbox' (default) and other folders via ?folder=...
    """
    folder = request.GET.get('folder', 'inbox')
    
    # Check HTMX
    is_htmx = request.headers.get('HX-Request')
    
    # CRM Filters
    company_filter = request.GET.get('company_filter', '').strip()
    contact_filter = request.GET.get('contact_filter', '').strip()
    email_filter = request.GET.get('email_filter', '').strip()
    
    # Check connection via GoogleChatCredentials (same as Chat/Drive)
    google_creds = GoogleChatCredentials.objects.filter(user=request.user).first()
    is_connected = google_creds is not None
    
    # Get or create EmailAccount from Google credentials
    email_account = None
    if is_connected:
        email_account, _ = EmailAccount.objects.get_or_create(
            user=request.user,
            defaults={
                'email_address': google_creds.email or '',
                'is_active': True,
                'access_token': google_creds.token,
                'refresh_token': google_creds.refresh_token,
            }
        )
        
        # Sync tokens and email
        update_fields = []
        if google_creds.token and email_account.access_token != google_creds.token:
            email_account.access_token = google_creds.token
            update_fields.append('access_token')
            
        if google_creds.refresh_token and email_account.refresh_token != google_creds.refresh_token:
            email_account.refresh_token = google_creds.refresh_token
            update_fields.append('refresh_token')
            
        if google_creds.email and email_account.email_address != google_creds.email:
            email_account.email_address = google_creds.email
            update_fields.append('email_address')
            
        if update_fields:
            email_account.save(update_fields=update_fields)
    
    # Get emails for the selected folder
    emails = []
    selected_email = None
    
    if is_connected and email_account:
        emails = Email.objects.filter(
            email_account=email_account,
            folder=folder
        ).select_related('company', 'contact').prefetch_related('attachments', 'companies', 'contacts')
        
        # Apply CRM filters
        if company_filter:
            emails = emails.filter(company__name__icontains=company_filter)
        if contact_filter:
            emails = emails.filter(contact__name__icontains=contact_filter)
        if email_filter:
            emails = emails.filter(
                models.Q(from_email__icontains=email_filter) |
                models.Q(to_emails__icontains=email_filter)
            )
    
    # Folder counts (Optimized: Single query)
    folder_counts = {}
    if is_connected and email_account:
        from django.db.models import Count, Q
        stats = Email.objects.filter(email_account=email_account).aggregate(
            inbox=Count('id', filter=Q(folder='inbox')),
            sent=Count('id', filter=Q(folder='sent')),
            archive=Count('id', filter=Q(folder='archive')),
            trash=Count('id', filter=Q(folder='trash')),
            unread=Count('id', filter=Q(folder='inbox', is_read=False))
        )
        folder_counts = {
            'inbox': stats['inbox'],
            'sent': stats['sent'],
            'archive': stats['archive'],
            'trash': stats['trash'],
            'unread': stats['unread']
        }
    
    # Pagination
    from django.core.paginator import Paginator
    page_number = request.GET.get('page', 1)
    paginator = Paginator(emails, 25)  # 25 emails per page
    page_obj = paginator.get_page(page_number)
    
    folder_labels = {
        'inbox': 'Inbox',
        'sent': 'Sent',
        'archive': 'Archive',
        'trash': 'Trash',
    }
    
    folder_icons = {
        'inbox': 'fas fa-inbox',
        'sent': 'fas fa-paper-plane',
        'archive': 'fas fa-archive',
        'trash': 'fas fa-trash',
    }
    
    context = {
        'emails': page_obj if page_obj else [],
        'page_obj': page_obj,
        'current_folder': folder,
        'folder_counts': folder_counts,
        'is_connected': is_connected,
        'email_account': email_account,
        'page_title': folder_labels.get(folder, 'My Emails'),
        'folder_icon': folder_icons.get(folder, 'fas fa-inbox'),
        'filter_company': company_filter,
        'filter_contact': contact_filter,
        'filter_email': email_filter,
        'is_htmx': is_htmx,
    }
    
    # Return partial for HTMX requests (sidebar navigation)
    if is_htmx:
        return render(request, 'email_automation/partials/my_emails_list.html', context)
    
    return render(request, 'email_automation/my_emails.html', context)


@login_required
def my_emails_sent(request):
    """Sent emails folder"""
    return my_emails_folder(request, 'sent')


@login_required
def my_emails_archive(request):
    """Archived emails folder"""
    return my_emails_folder(request, 'archive')


@login_required
def my_emails_trash(request):
    """Trash folder"""
    return my_emails_folder(request, 'trash')


def my_emails_folder(request, folder):
    """Helper function for folder views"""
    # Get user's email account
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        is_connected = True
        
        # Sync token if needed (light check)
        google_creds = GoogleChatCredentials.objects.filter(user=request.user).first()
        if google_creds and google_creds.token and email_account.access_token != google_creds.token:
            email_account.access_token = google_creds.token
            email_account.save(update_fields=['access_token'])
            
    except EmailAccount.DoesNotExist:
        email_account = None
        is_connected = False
    
    # Check HTMX
    is_htmx = request.headers.get('HX-Request')
    
    emails = []
    selected_email = None
    
    if is_connected and email_account:
        emails = Email.objects.filter(
            email_account=email_account,
            folder=folder
        ).select_related('company', 'contact').prefetch_related('attachments', 'companies', 'contacts')
    
    # Folder counts (Optimized)
    folder_counts = {}
    if is_connected and email_account:
        from django.db.models import Count, Q
        stats = Email.objects.filter(email_account=email_account).aggregate(
            inbox=Count('id', filter=Q(folder='inbox')),
            sent=Count('id', filter=Q(folder='sent')),
            archive=Count('id', filter=Q(folder='archive')),
            trash=Count('id', filter=Q(folder='trash')),
            unread=Count('id', filter=Q(folder='inbox', is_read=False))
        )
        folder_counts = {
            'inbox': stats['inbox'],
            'sent': stats['sent'],
            'archive': stats['archive'],
            'trash': stats['trash'],
            'unread': stats['unread']
        }
    
    # Pagination
    from django.core.paginator import Paginator
    page_number = request.GET.get('page', 1)
    paginator = Paginator(emails, 25)
    page_obj = paginator.get_page(page_number)
    
    folder_labels = {
        'inbox': 'Inbox',
        'sent': 'Sent',
        'archive': 'Archive',
        'trash': 'Trash',
    }
    
    folder_icons = {
        'inbox': 'fas fa-inbox',
        'sent': 'fas fa-paper-plane',
        'archive': 'fas fa-archive',
        'trash': 'fas fa-trash',
    }
    
    context = {
        'emails': page_obj if page_obj else [],
        'page_obj': page_obj,
        'current_folder': folder,
        'folder_counts': folder_counts,
        'is_connected': is_connected,
        'email_account': email_account,
        'page_title': folder_labels.get(folder, 'My Emails'),
        'folder_icon': folder_icons.get(folder, 'fas fa-inbox'),
        'filter_company': '',
        'filter_contact': '',
        'filter_email': '',
        'is_htmx': is_htmx,
    }
    
    # Return partial for HTMX requests
    if is_htmx:
        return render(request, 'email_automation/partials/my_emails_list.html', context)
    
    return render(request, 'email_automation/my_emails.html', context)


@login_required
def compose_email(request):
    """Compose new email - returns modal HTML or full page"""
    # Get recipient from query params (for CRM integration)
    recipient_email = request.GET.get('to', '')
    recipient_name = request.GET.get('name', '')
    company_id = request.GET.get('company')
    contact_id = request.GET.get('contact')
    
    # Pre-fill subject if replying
    subject = request.GET.get('subject', '')
    
    # Check if connected
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        is_connected = True
    except EmailAccount.DoesNotExist:
        email_account = None
        is_connected = False
    
    context = {
        'recipient_email': recipient_email,
        'recipient_name': recipient_name,
        'subject': subject,
        'company_id': company_id,
        'contact_id': contact_id,
        'is_connected': is_connected,
        'email_account': email_account,
    }
    
    # Return modal partial for HTMX requests
    if request.headers.get('HX-Request'):
        return render(request, 'email_automation/partials/compose_modal.html', context)
    
    return render(request, 'email_automation/compose.html', context)


@login_required
def send_email_view(request):
    """Send email via Gmail - AJAX endpoint"""
    from .gmail_utils import send_email as gmail_send_email
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    # Get the EmailAccount (created during Gmail OAuth flow with correct tokens)
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        print(f"[SEND] Found EmailAccount: {email_account.email_address}")
    except EmailAccount.DoesNotExist:
        print("[SEND] ERROR: No EmailAccount found")
        return JsonResponse({'error': 'Gmail account not connected. Please connect from Mail settings page.'}, status=400)
    
    if not email_account.access_token:
        print("[SEND] ERROR: No access token")
        return JsonResponse({'error': 'Gmail tokens missing. Please reconnect your account.'}, status=400)
    
    print(f"[SEND] Token present: {bool(email_account.access_token)}, Refresh: {bool(email_account.refresh_token)}")
    
    # Get form data
    to_emails = request.POST.getlist('to[]') or [request.POST.get('to', '')]
    cc_emails = request.POST.getlist('cc[]', [])
    bcc_emails = request.POST.getlist('bcc[]', [])
    subject = request.POST.get('subject', '')
    body = request.POST.get('body', '')
    company_id = request.POST.get('company_id')
    contact_id = request.POST.get('contact_id')
    
    # Filter empty emails
    to_emails = [e.strip() for e in to_emails if e.strip()]
    cc_emails = [e.strip() for e in cc_emails if e.strip()]
    bcc_emails = [e.strip() for e in bcc_emails if e.strip()]
    
    print(f"[SEND] To: {to_emails}, Cc: {cc_emails}, Subject: {subject[:50]}")
    
    if not to_emails:
        return JsonResponse({'error': 'Recipient email address is required'}, status=400)
    
    if not subject:
        return JsonResponse({'error': 'Subject is required'}, status=400)
    
    try:
        # Get Gmail service
        from .gmail_utils import get_gmail_service
        print("[SEND] Getting Gmail service...")
        service = get_gmail_service(email_account)
        
        if not service:
            print("[SEND] ERROR: get_gmail_service returned None")
            return JsonResponse({'error': 'Could not connect to Gmail. Please reconnect your account from Settings.'}, status=500)
        
        print("[SEND] Gmail service obtained successfully")
        
        # Prepare attachments for Gmail
        files = request.FILES.getlist('attachments')
        email_attachments = []
        
        for file in files:
            # Read file content for Gmail API
            content = file.read()
            email_attachments.append((file.name, content, file.content_type))
            # Reset file pointer for subsequent operations
            file.seek(0)
            
        # Send via Gmail
        print(f"[SEND] Calling gmail_send_email to {to_emails[0]}...")
        sent_message = gmail_send_email(
            service=service,
            sender=email_account.email_address,
            to=to_emails[0],  # Primary recipient
            subject=subject,
            message_text=body,
            html_body=body,
            cc=cc_emails,
            bcc=bcc_emails,
            attachments=email_attachments
        )
        
        print(f"[SEND] Gmail API response: {sent_message}")
        
        if not sent_message:
            return JsonResponse({'error': 'Gmail API returned no response. Your token may have expired. Please reconnect from Settings.'}, status=500)
            
        gmail_message_id = sent_message['id']
        gmail_thread_id = sent_message.get('threadId')
        
        # Create Email record
        email = Email.objects.create(
            email_account=email_account,
            gmail_message_id=gmail_message_id,
            gmail_thread_id=gmail_thread_id,
            from_email=email_account.email_address,
            from_name=request.user.get_full_name() or request.user.username,
            to_emails=to_emails,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails,
            subject=subject,
            body_text=body,
            body_html=body,
            folder='sent',
            is_read=True,
            sent_at=timezone.now(),
        )
        
        # Link to CRM records
        if company_id:
            try:
                email.company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                pass
        
        if contact_id:
            try:
                email.contact = Contact.objects.get(pk=contact_id)
            except Contact.DoesNotExist:
                pass
        
        # Try to auto-match CRM records
        if not email.company and not email.contact:
            email.match_crm_records()
        
        email.save()
        
        # Handle file attachments - Upload to Cloudinary for record
        # Note: Email already sent above, so failures here shouldn't crash
        
        for file in files:
            try:
                # Upload to Cloudinary
                import cloudinary.uploader
                
                # Check if Cloudinary is configured
                if not settings.CLOUDINARY_STORAGE.get('CLOUD_NAME'):
                    raise Exception("Cloudinary not configured")
                    
                result = cloudinary.uploader.upload(
                    file,
                    folder='email_attachments',
                    resource_type='auto'
                )
                
                file_url = result['secure_url']
            except Exception as e:
                print(f"Cloudinary upload failed: {e}")
                # Fallback: Use a local path or placeholder if upload fails
                # For now just use a placeholder to avoid crashing
                file_url = f"#upload-failed-{file.name}"
            
            EmailAttachment.objects.create(
                email=email,
                filename=file.name,
                file_url=file_url,
                file_size=file.size,
                content_type=file.content_type,
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Email sent successfully',
            'email_id': email.id,
        })
        
    except RefreshError:
        return JsonResponse({'error': 'Your Google connection has expired. Please reconnect your account from Settings.'}, status=401)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def email_detail(request, pk):
    """Get email detail - AJAX or full page"""
    try:
        email_account = EmailAccount.objects.get(user=request.user)
    except EmailAccount.DoesNotExist:
        if request.headers.get('HX-Request'):
            return render(request, 'email_automation/partials/email_detail.html', {'error': 'Not connected'})
        return redirect('email_automation:my_emails')
    
    email = get_object_or_404(
        Email.objects.select_related('company', 'contact').prefetch_related('companies', 'contacts', 'attachments'), 
        pk=pk, 
        email_account=email_account
    )
    
    # Mark as read
    if not email.is_read:
        email.is_read = True
        email.save()
    
    context = {
        'email': email,
        'attachments': email.attachments.all(),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'email_automation/partials/email_detail.html', context)
    
    return render(request, 'email_automation/email_detail.html', context)


@login_required
def move_email(request, pk):
    """Move email to different folder - AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        email_account = EmailAccount.objects.get(user=request.user)
    except EmailAccount.DoesNotExist:
        return JsonResponse({'error': 'Not connected'}, status=400)
    
    email = get_object_or_404(Email, pk=pk, email_account=email_account)
    
    folder = request.POST.get('folder')
    if folder not in ['inbox', 'archive', 'trash']:
        return JsonResponse({'error': 'Invalid folder'}, status=400)
    
    email.folder = folder
    email.save()
    
    folder_labels = {
        'inbox': 'Inbox',
        'archive': 'Archive',
        'trash': 'Trash',
    }
    
    return JsonResponse({
        'success': True,
        'message': f'Email moved to {folder_labels.get(folder)}',
    })


@login_required
def bulk_move_emails(request):
    """Move multiple emails to a folder - AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        email_account = EmailAccount.objects.get(user=request.user)
    except EmailAccount.DoesNotExist:
        return JsonResponse({'error': 'Not connected'}, status=400)
    
    try:
        data = json.loads(request.body)
        email_ids = data.get('email_ids', [])
        folder = data.get('folder', '')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    if folder not in ['inbox', 'archive', 'trash']:
        return JsonResponse({'error': 'Invalid folder'}, status=400)
    
    if not email_ids:
        return JsonResponse({'error': 'No emails selected'}, status=400)
    
    count = Email.objects.filter(
        pk__in=email_ids,
        email_account=email_account
    ).update(folder=folder)
    
    folder_labels = {
        'inbox': 'Inbox',
        'archive': 'Archive',
        'trash': 'Trash',
    }
    
    return JsonResponse({
        'success': True,
        'count': count,
        'message': f'{count} email{"s" if count != 1 else ""} moved to {folder_labels.get(folder)}',
    })


@login_required
def delete_email_view(request, pk):
    """Delete email permanently - AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        email_account = EmailAccount.objects.get(user=request.user)
    except EmailAccount.DoesNotExist:
        return JsonResponse({'error': 'Not connected'}, status=400)
    
    email = get_object_or_404(Email, pk=pk, email_account=email_account)
    
    # If already in trash, delete permanently
    if email.folder == 'trash':
        email.delete()
        return JsonResponse({'success': True, 'message': 'Email permanently deleted'})
    
    # Otherwise move to trash
    email.folder = 'trash'
    email.save()
    
    return JsonResponse({'success': True, 'message': 'Email moved to Trash'})


@login_required
def toggle_star(request, pk):
    """Toggle star status - AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        email_account = EmailAccount.objects.get(user=request.user)
    except EmailAccount.DoesNotExist:
        return JsonResponse({'error': 'Not connected'}, status=400)
    
    email = get_object_or_404(Email, pk=pk, email_account=email_account)
    email.is_starred = not email.is_starred
    email.save()
    
    return JsonResponse({
        'success': True,
        'is_starred': email.is_starred,
    })


# ============================================================
# CRM INTEGRATION VIEWS
# ============================================================

@login_required
def company_emails(request, company_id):
    """Get emails related to a company - for Communication tab"""
    company = get_object_or_404(Company, pk=company_id)
    
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        emails = Email.objects.filter(
            email_account=email_account,
            company=company
        ).exclude(folder='trash').order_by('-created_at')[:50]
    except EmailAccount.DoesNotExist:
        emails = []
    
    context = {
        'emails': emails,
        'company': company,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'email_automation/partials/company_emails.html', context)
    
    return JsonResponse({
        'emails': [{
            'id': e.id,
            'subject': e.subject,
            'from_email': e.from_email,
            'to_emails': e.to_emails,
            'snippet': e.get_preview(100),
            'sent_at': e.sent_at.isoformat() if e.sent_at else None,
            'received_at': e.received_at.isoformat() if e.received_at else None,
            'folder': e.folder,
            'is_read': e.is_read,
            'attachment_count': e.attachments.count(),
        } for e in emails]
    })


@login_required
def company_shared_files(request, company_id):
    """Get files shared via email with a company"""
    company = get_object_or_404(Company, pk=company_id)
    
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        attachments = EmailAttachment.objects.filter(
            email__email_account=email_account,
            email__company=company
        ).select_related('email').order_by('-uploaded_at')[:50]
    except EmailAccount.DoesNotExist:
        attachments = []
    
    context = {
        'attachments': attachments,
        'company': company,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'email_automation/partials/company_files.html', context)
    
    return JsonResponse({
        'files': [{
            'id': a.id,
            'filename': a.filename,
            'file_url': a.file_url,
            'file_size': a.get_size_display(),
            'content_type': a.content_type,
            'email_subject': a.email.subject,
            'uploaded_at': a.uploaded_at.isoformat(),
        } for a in attachments]
    })


@login_required
def contact_emails(request, contact_id):
    """Get emails related to a contact"""
    contact = get_object_or_404(Contact, pk=contact_id)
    
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        emails = Email.objects.filter(
            email_account=email_account,
            contact=contact
        ).exclude(folder='trash').order_by('-created_at')[:50]
    except EmailAccount.DoesNotExist:
        emails = []
    
    context = {
        'emails': emails,
        'contact': contact,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'email_automation/partials/contact_emails.html', context)
    
    return JsonResponse({
        'emails': [{
            'id': e.id,
            'subject': e.subject,
            'from_email': e.from_email,
            'to_emails': e.to_emails,
            'snippet': e.get_preview(100),
            'sent_at': e.sent_at.isoformat() if e.sent_at else None,
            'received_at': e.received_at.isoformat() if e.received_at else None,
            'folder': e.folder,
            'is_read': e.is_read,
        } for e in emails]
    })


@login_required
def contact_shared_files(request, contact_id):
    """Get files shared via email with a contact"""
    contact = get_object_or_404(Contact, pk=contact_id)
    
    try:
        email_account = EmailAccount.objects.get(user=request.user)
        attachments = EmailAttachment.objects.filter(
            email__email_account=email_account,
            email__contact=contact
        ).select_related('email').order_by('-uploaded_at')[:50]
    except EmailAccount.DoesNotExist:
        attachments = []
    
    context = {
        'attachments': attachments,
        'contact': contact,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'email_automation/partials/company_files.html', context)
    
    return JsonResponse({
        'files': [{
            'id': a.id,
            'filename': a.filename,
            'file_url': a.file_url,
            'file_size': a.get_size_display(),
            'content_type': a.content_type,
            'email_subject': a.email.subject,
            'uploaded_at': a.uploaded_at.isoformat(),
        } for a in attachments]
    })


@login_required
def api_recipients(request):
    """Autocomplete API for recipient search - returns contacts and companies"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    results = []
    
    # Search contacts
    contacts = Contact.objects.filter(
        models.Q(name__icontains=query) | models.Q(email__icontains=query)
    ).select_related('company')[:10]
    
    for contact in contacts:
        # Contact.email is an ArrayField — extract first email
        email = ''
        if contact.email:
            if isinstance(contact.email, list):
                email = contact.email[0] if contact.email else ''
            else:
                email = contact.email
        results.append({
            'type': 'contact',
            'id': contact.id,
            'name': contact.name,
            'email': email,
            'company': contact.company.name if contact.company else '',
        })
    
    # Search companies
    companies = Company.objects.filter(
        models.Q(name__icontains=query) | models.Q(email__icontains=query)
    )[:10]
    
    for company in companies:
        email = company.email[0] if company.email else ''
        results.append({
            'type': 'company',
            'id': company.id,
            'name': company.name,
            'email': email,
        })
    
    return JsonResponse(results, safe=False)
    
@login_required
def sync_emails(request):
    """Sync emails from Gmail - AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        email_account = EmailAccount.objects.get(user=request.user)
    except EmailAccount.DoesNotExist:
        return JsonResponse({'error': 'Not connected'}, status=400)
    
    try:
        # Import here to avoid circular import if placed at top
        from .gmail_utils import fetch_inbox_emails
        
        count = fetch_inbox_emails(email_account, max_results=20)
        
        response = JsonResponse({
            'success': True,
            'message': f'{count} new emails synced',
            'count': count
        })
        # Trigger HTMX to refresh the email list
        response['HX-Trigger'] = 'emailsSynced'
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def download_attachment(request, pk):
    """
    Download attachment, falling back to Gmail API if file_url is not available
    """
    from .models import EmailAttachment
    attachment = get_object_or_404(EmailAttachment, pk=pk)
    
    # Check if user owns the email via account
    if attachment.email.email_account.user != request.user:
         return HttpResponseForbidden()

    # 1. Try redirect if URL is valid and not a placeholder
    if attachment.file_url and not attachment.file_url.startswith('#') and 'upload-failed' not in attachment.file_url:
         return redirect(attachment.file_url)

    # 2. Fallback to Gmail API
    try:
        email_account = attachment.email.email_account
        service = gmail_utils.get_gmail_service(email_account)
        
        gmail_att_id = attachment.gmail_attachment_id
        
        if not gmail_att_id:
            # Fetch message details to find attachment ID
            if not attachment.email.gmail_message_id:
                raise Http404("Original message ID not found")
                
            msg = gmail_utils.get_message(service, attachment.email.gmail_message_id)
            if not msg:
                 raise Http404("Message not found in Gmail")
                 
            # Find attachment by filename
            parts = msg.get('payload', {}).get('parts', [])
            
            def find_att_id(parts, filename):
                for part in parts:
                    if part.get('filename') == filename and part.get('body', {}).get('attachmentId'):
                        return part['body'].get('attachmentId')
                    if part.get('parts'):
                        found = find_att_id(part['parts'], filename)
                        if found: return found
                return None

            gmail_att_id = find_att_id(parts, attachment.filename)
            
            if gmail_att_id:
                 # Save it for next time
                 attachment.gmail_attachment_id = gmail_att_id
                 attachment.save(update_fields=['gmail_attachment_id'])
        
        if gmail_att_id:
             data = gmail_utils.get_attachment(service, attachment.email.gmail_message_id, gmail_att_id)
             if data:
                 response = HttpResponse(data, content_type=attachment.content_type or 'application/octet-stream')
                 response['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
                 return response
    except Exception as e:
        print(f"Error downloading attachment: {e}")
        pass

    raise Http404("Attachment not found or could not be downloaded")
