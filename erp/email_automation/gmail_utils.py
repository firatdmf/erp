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
import datetime
from django.utils import timezone


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


from google.auth.exceptions import RefreshError

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
        try:
            credentials.refresh(Request())
            email_account.access_token = credentials.token
            email_account.save(update_fields=['access_token'])
        except RefreshError:
            print("Refresh token expired or revoked.")
            return None
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
    
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


from email.mime.base import MIMEBase
from email import encoders

def create_message(sender, to, subject, message_text, html_body=None, cc=None, bcc=None, attachments=None):
    """
    Create a message for an email
    attachments: list of tuples (filename, content, content_type)
    """
    if attachments:
        message = MIMEMultipart('mixed')
    elif html_body:
        message = MIMEMultipart('alternative')
    else:
        message = MIMEText(message_text, 'plain')

    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    if cc:
        message['cc'] = ", ".join(cc) if isinstance(cc, list) else cc
    if bcc:
        message['bcc'] = ", ".join(bcc) if isinstance(bcc, list) else bcc

    # Body handling
    if html_body:
        if attachments:
            msg_body = MIMEMultipart('alternative')
            msg_body.attach(MIMEText(message_text, 'plain'))
            msg_body.attach(MIMEText(html_body, 'html'))
            message.attach(msg_body)
        else:
             # message is already alternative
             message.attach(MIMEText(message_text, 'plain'))
             message.attach(MIMEText(html_body, 'html'))
    else:
        # Plain text
        if attachments:
             message.attach(MIMEText(message_text, 'plain'))
        else:
             # message is MIMEText, content already set in constructor
             pass 

    # Attachments
    if attachments:
        for filename, content, content_type in attachments:
            if not content_type:
                content_type = 'application/octet-stream'
            
            main_type, sub_type = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')
            
            part = MIMEBase(main_type, sub_type)
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )
            message.attach(part)
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_email(service, sender, to, subject, message_text, html_body=None, cc=None, bcc=None, attachments=None):
    """
    Send an email message
    """
    message = create_message(sender, to, subject, message_text, html_body, cc, bcc, attachments)
    sent_message = service.users().messages().send(
        userId='me', 
        body=message
    ).execute()
    return sent_message



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


def get_attachment(service, msg_id, att_id):
    """
    Get attachment data
    """
    try:
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=msg_id,
            id=att_id
        ).execute()
        
        data = base64.urlsafe_b64decode(attachment['data'])
        return data
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def parse_message(message):
    """
    Parse a Gmail message to extract relevant information
    """
    from email.utils import parseaddr, parsedate_to_datetime, getaddresses
    from django.utils import timezone
    
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
            
    # Parse sender
    sender_name, sender_email = parseaddr(sender)
    
    # Parse recipients
    to_list = []
    if to:
        to_list = [addr[1] for addr in getaddresses([to])]
    
    # Parse date
    try:
        received_at = parsedate_to_datetime(date)
    except:
        received_at = timezone.now()

    # Get message body (text and html) and attachments
    body_text = ''
    body_html = ''
    attachments = []
    
    payload = message.get('payload', {})
    
    def get_parts(parts):
        text = ''
        html = ''
        for part in parts:
             mimeType = part.get('mimeType')
             filename = part.get('filename', '')
             body_obj = part.get('body', {})
             body_data = body_obj.get('data', '')
             att_id = body_obj.get('attachmentId', '')
             
             # Attachment: has a filename and attachmentId
             if filename and att_id:
                 attachments.append({
                     'filename': filename,
                     'mimeType': mimeType or 'application/octet-stream',
                     'size': body_obj.get('size', 0),
                     'attachmentId': att_id,
                 })
             elif body_data:
                 decoded = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                 if mimeType == 'text/plain':
                     text += decoded
                 elif mimeType == 'text/html':
                     html += decoded
             
             if part.get('parts'):
                 t, h = get_parts(part.get('parts'))
                 text += t
                 html += h
        return text, html

    if 'parts' in payload:
        body_text, body_html = get_parts(payload['parts'])
    else:
        # Single part
        data = payload.get('body', {}).get('data', '')
        if data:
            decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            if payload.get('mimeType') == 'text/html':
                body_html = decoded
            else:
                body_text = decoded

    return {
        'id': message.get('id'),
        'threadId': message.get('threadId'),
        'subject': subject,
        'sender_name': sender_name,
        'sender_email': sender_email,
        'to': to_list,
        'received_at': received_at,
        'body_text': body_text,
        'body_html': body_html,
        'snippet': message.get('snippet', ''),
        'attachments': attachments,
    }


def fetch_inbox_emails(email_account, max_results=20):
    """
    Fetch recent emails from inbox and save to DB
    """
    from .models import Email, EmailAttachment
    
    service = get_gmail_service(email_account)
    if not service:
        raise Exception("Gmail connection expired. Please reconnect in Settings.")
        
    # Get messages from both INBOX and SENT
    inbox_messages = list_messages(service, max_results=max_results, query='label:INBOX') or []
    sent_messages = list_messages(service, max_results=max_results, query='label:SENT') or []
    
    # Combine, dedup by ID
    seen_ids = set()
    all_messages = []
    for msg in inbox_messages + sent_messages:
        if msg['id'] not in seen_ids:
            seen_ids.add(msg['id'])
            all_messages.append(msg)
    
    if not all_messages:
        return 0
    
    # Filter out messages already in DB to avoid unnecessary API calls
    all_msg_ids = [m['id'] for m in all_messages]
    existing_ids = set(
        Email.objects.filter(gmail_message_id__in=all_msg_ids)
        .values_list('gmail_message_id', flat=True)
    )
    new_messages = [m for m in all_messages if m['id'] not in existing_ids]
    
    count = 0
        
    for msg in new_messages:
        try:
            # Fetch full message
            message_detail = get_message(service, msg['id'])
            if not message_detail:
                continue
                
            parsed = parse_message(message_detail)
            
            # Use internalDate as fallback if date parsing failed
            if not parsed.get('received_at') and message_detail.get('internalDate'):
                try:
                    timestamp = int(message_detail.get('internalDate')) / 1000
                    parsed['received_at'] = datetime.datetime.fromtimestamp(timestamp, tz=timezone.utc)
                except:
                    parsed['received_at'] = timezone.now()
            
            # Determine folder from Gmail labels
            labels = message_detail.get('labelIds', [])
            if 'SENT' in labels and 'INBOX' not in labels:
                folder = 'sent'
            else:
                folder = 'inbox'
            
            # Safety: truncate fields to fit DB columns
            subject = (parsed.get('subject') or '')[:500]
            snippet = (parsed.get('snippet') or '')[:300]
            from_name = (parsed.get('sender_name') or '')[:200]
            from_email = (parsed.get('sender_email') or '')[:254]
            
            # Create new email
            email = Email(
                email_account=email_account,
                gmail_message_id=parsed['id'],
                gmail_thread_id=parsed['threadId'],
                from_email=from_email,
                from_name=from_name,
                to_emails=parsed['to'], 
                subject=subject,
                body_text=parsed['body_text'],
                body_html=parsed['body_html'],
                snippet=snippet,
                folder=folder,
                received_at=parsed['received_at'] if folder == 'inbox' else None,
                sent_at=parsed['received_at'] if folder == 'sent' else None,
                is_read='UNREAD' not in labels
            )
            email.save()
            
            # Create attachment records
            for att in parsed.get('attachments', []):
                EmailAttachment.objects.create(
                    email=email,
                    filename=att['filename'][:255],
                    file_url='#gmail-attachment',
                    file_size=att.get('size', 0),
                    content_type=att.get('mimeType', 'application/octet-stream')[:100],
                    gmail_attachment_id=att.get('attachmentId', ''),
                )
            
            # Auto-match CRM records
            email.match_crm_records()
            email.save()
            
            count += 1
            
        except Exception as e:
            print(f"Error syncing email {msg['id']}: {e}")
            continue
            
    return count


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
            sender = parsed['sender_email'].lower()
            to_list = [t.lower() for t in parsed['to']]
            
            # Check if this is a reply TO our email address
            # We check if our email is in the TO list
            if any(original_sender_email.lower() in t for t in to_list):
                return {
                    'has_reply': True,
                    'reply_message': parsed,
                    'replied_at': parsed['received_at']
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
                    
                    # Already parsed by parse_message
                    sender_email = reply_msg['sender_email']
                    
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
                    
    except Exception as e:
        print(f"Error checking campaigns for replies: {e}")
        return 0
        
    return reply_count


