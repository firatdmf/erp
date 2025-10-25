from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import EmailAccount, EmailTemplate, EmailCampaign, SentEmail, ReceivedEmail
from crm.models import Company
import json


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
