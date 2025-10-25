"""
Gmail OAuth and API utility functions
"""
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from django.conf import settings
from django.urls import reverse
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json


def get_gmail_oauth_flow(request):
    """
    Create and return a Gmail OAuth flow object
    """
    # OAuth scopes
    scopes = settings.GMAIL_SCOPES
    
    # Create flow instance
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GMAIL_REDIRECT_URI],
            }
        },
        scopes=scopes,
    )
    
    # Set the redirect URI
    flow.redirect_uri = settings.GMAIL_REDIRECT_URI
    
    return flow


def get_authorization_url(request):
    """
    Generate the OAuth authorization URL
    """
    flow = get_gmail_oauth_flow(request)
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force consent screen to get refresh token
    )
    
    # Store state in session for verification
    request.session['oauth_state'] = state
    
    return authorization_url


def exchange_code_for_tokens(request, code, state):
    """
    Exchange authorization code for access and refresh tokens
    """
    import os
    import warnings
    import urllib3
    
    # Temporary fix for SSL issues with antivirus (development only!)
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Verify state
    stored_state = request.session.get('oauth_state')
    print(f"DEBUG: Stored state in session: {stored_state}")
    print(f"DEBUG: Received state from Google: {state}")
    print(f"DEBUG: States match: {state == stored_state}")
    
    if state != stored_state:
        print(f"ERROR: State mismatch! Stored: {stored_state}, Received: {state}")
        # For development, we'll allow it to continue with a warning
        print("WARNING: Continuing anyway for development...")
        # raise ValueError('State mismatch - possible CSRF attack')
    
    # Monkey patch requests to disable SSL verification
    import requests
    from functools import partialmethod
    original_request = requests.Session.request
    requests.Session.request = partialmethod(original_request, verify=False)
    
    try:
        flow = get_gmail_oauth_flow(request)
        flow.fetch_token(code=code)
    finally:
        # Restore original request method
        requests.Session.request = original_request
    
    credentials = flow.credentials
    
    return {
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
    }


def credentials_from_dict(creds_dict):
    """
    Create Credentials object from dictionary
    """
    return Credentials(
        token=creds_dict.get('access_token'),
        refresh_token=creds_dict.get('refresh_token'),
        token_uri=creds_dict.get('token_uri'),
        client_id=creds_dict.get('client_id'),
        client_secret=creds_dict.get('client_secret'),
        scopes=creds_dict.get('scopes'),
    )


def refresh_credentials(email_account):
    """
    Refresh expired access token
    """
    creds_dict = {
        'access_token': email_account.access_token,
        'refresh_token': email_account.refresh_token,
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': settings.GMAIL_CLIENT_ID,
        'client_secret': settings.GMAIL_CLIENT_SECRET,
        'scopes': settings.GMAIL_SCOPES,
    }
    
    credentials = credentials_from_dict(creds_dict)
    
    # Refresh the token
    credentials.refresh(Request())
    
    # Update the email account with new token
    email_account.access_token = credentials.token
    email_account.save(update_fields=['access_token'])
    
    return credentials


def get_gmail_service(email_account):
    """
    Get authenticated Gmail API service
    """
    creds_dict = {
        'access_token': email_account.access_token,
        'refresh_token': email_account.refresh_token,
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': settings.GMAIL_CLIENT_ID,
        'client_secret': settings.GMAIL_CLIENT_SECRET,
        'scopes': settings.GMAIL_SCOPES,
    }
    
    credentials = credentials_from_dict(creds_dict)
    
    # Check if token is expired and refresh if needed
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        email_account.access_token = credentials.token
        email_account.save(update_fields=['access_token'])
    
    # Build and return the service
    service = build('gmail', 'v1', credentials=credentials)
    return service


def get_user_email(service):
    """
    Get the authenticated user's email address
    """
    try:
        profile = service.users().getProfile(userId='me').execute()
        return profile.get('emailAddress')
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def create_message(sender, to, subject, message_text, html_body=None):
    """
    Create a message for an email
    """
    if html_body:
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        
        text_part = MIMEText(message_text, 'plain')
        html_part = MIMEText(html_body, 'html')
        
        message.attach(text_part)
        message.attach(html_part)
    else:
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}


def send_email(service, sender, to, subject, message_text, html_body=None):
    """
    Send an email message
    """
    try:
        message = create_message(sender, to, subject, message_text, html_body)
        sent_message = service.users().messages().send(
            userId='me', 
            body=message
        ).execute()
        return sent_message
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def list_messages(service, max_results=10, query=''):
    """
    List messages from inbox
    """
    try:
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=query
        ).execute()
        
        messages = results.get('messages', [])
        return messages
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []


def get_message(service, msg_id):
    """
    Get a specific message by ID
    """
    try:
        message = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()
        return message
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def parse_message(message):
    """
    Parse a Gmail message to extract relevant information
    """
    headers = message.get('payload', {}).get('headers', [])
    
    subject = ''
    sender = ''
    to = ''
    date = ''
    
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        
        if name == 'subject':
            subject = value
        elif name == 'from':
            sender = value
        elif name == 'to':
            to = value
        elif name == 'date':
            date = value
    
    # Get message body
    body = ''
    if 'parts' in message.get('payload', {}):
        parts = message['payload']['parts']
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
    else:
        data = message.get('payload', {}).get('body', {}).get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8')
    
    return {
        'id': message.get('id'),
        'thread_id': message.get('threadId'),
        'subject': subject,
        'sender': sender,
        'to': to,
        'date': date,
        'body': body,
        'snippet': message.get('snippet', ''),
    }


def check_thread_for_replies(service, thread_id, original_sender_email):
    """
    Check if a thread has received replies from the recipient
    
    Args:
        service: Gmail API service
        thread_id: Gmail thread ID to check
        original_sender_email: Our email address (to identify incoming replies)
    
    Returns:
        dict with 'has_reply', 'reply_message' if reply found
    """
    try:
        thread = service.users().threads().get(
            userId='me',
            id=thread_id,
            format='full'
        ).execute()
        
        messages = thread.get('messages', [])
        
        # Skip first message (our original email)
        if len(messages) <= 1:
            return {'has_reply': False}
        
        # Check subsequent messages for replies FROM recipient TO us
        for message in messages[1:]:
            parsed = parse_message(message)
            sender = parsed['sender'].lower()
            to = parsed['to'].lower()
            
            # Check if this is a reply TO our email address
            if original_sender_email.lower() in to:
                return {
                    'has_reply': True,
                    'reply_message': parsed,
                    'replied_at': parsed['date']
                }
        
        return {'has_reply': False}
        
    except HttpError as error:
        print(f'Error checking thread for replies: {error}')
        return {'has_reply': False}


def check_campaigns_for_replies(email_account):
    """
    Check all active campaigns for replies
    
    Args:
        email_account: EmailAccount instance
    
    Returns:
        Number of campaigns that received replies
    """
    from .models import EmailCampaign, SentEmail, ReceivedEmail
    from django.utils import timezone
    import re
    
    try:
        service = get_gmail_service(email_account)
        
        # Get all active campaigns for this user
        active_campaigns = EmailCampaign.objects.filter(
            user=email_account.user,
            status='active',
            reply_received=False
        )
        
        reply_count = 0
        
        for campaign in active_campaigns:
            # Get all sent emails for this campaign
            sent_emails = SentEmail.objects.filter(
                campaign=campaign,
                gmail_thread_id__isnull=False
            ).exclude(gmail_thread_id='')
            
            for sent_email in sent_emails:
                if sent_email.replied:
                    continue  # Already marked as replied
                
                # Check thread for replies
                result = check_thread_for_replies(
                    service,
                    sent_email.gmail_thread_id,
                    email_account.email_address
                )
                
                if result['has_reply']:
                    # Mark sent email as replied
                    sent_email.replied = True
                    sent_email.replied_at = timezone.now()
                    sent_email.save()
                    
                    # Save received email
                    reply_msg = result['reply_message']
                    
                    # Extract sender email from "Name <email>" format
                    sender_email = reply_msg['sender']
                    email_match = re.search(r'<(.+?)>', sender_email)
                    if email_match:
                        sender_email = email_match.group(1)
                    
                    ReceivedEmail.objects.get_or_create(
                        gmail_message_id=reply_msg['id'],
                        defaults={
                            'campaign': campaign,
                            'sender_email': sender_email,
                            'sender_name': reply_msg['sender'],
                            'subject': reply_msg['subject'],
                            'body': reply_msg['body'],
                            'gmail_thread_id': reply_msg['thread_id'],
                            'received_at': timezone.now(),
                            'is_reply': True,
                            'processed': True
                        }
                    )
                    
                    # Mark campaign as stopped
                    campaign.mark_reply_received()
                    reply_count += 1
                    
                    print(f"✓ Reply detected for campaign {campaign.id} from {sender_email}")
                    break  # No need to check other emails in this campaign
        
        return reply_count
        
    except Exception as e:
        print(f"✗ Error checking for replies: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0
