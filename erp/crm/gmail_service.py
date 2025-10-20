"""
Gmail API integration for detecting replies from prospect companies.
"""
import os
import pickle
import base64
from email.utils import parseaddr
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# Gmail API scope - readonly access to check for replies
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Path to store OAuth tokens
TOKEN_PATH = os.path.join(settings.BASE_DIR, 'gmail_token.pickle')
CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, 'gmail_credentials.json')


class GmailReplyDetector:
    """Service to detect replies from prospect companies using Gmail API."""
    
    def __init__(self):
        self.service = None
        self.user_email = getattr(settings, 'EMAIL_HOST_USER', '')
    
    def authenticate(self):
        """
        Authenticate with Gmail API using OAuth 2.0.
        Returns True if authentication successful, False otherwise.
        """
        creds = None
        
        # Load existing credentials from token file
        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh Gmail credentials: {e}")
                    return False
            else:
                if not os.path.exists(CREDENTIALS_PATH):
                    logger.error(f"Gmail credentials file not found at {CREDENTIALS_PATH}")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_PATH, SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Failed to authenticate with Gmail: {e}")
                    return False
            
            # Save credentials for next time
            with open(TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            return False
    
    def check_for_replies(self, company_email, sent_email_message_id=None, hours_back=168):
        """
        Check if a company has replied to our emails.
        
        Args:
            company_email: Email address of the company
            sent_email_message_id: Optional message ID of the email we sent (for thread matching)
            hours_back: How many hours back to search (default 7 days)
        
        Returns:
            dict: {
                'has_reply': bool,
                'reply_date': datetime or None,
                'message_snippet': str or None
            }
        """
        if not self.service:
            if not self.authenticate():
                return {'has_reply': False, 'reply_date': None, 'message_snippet': None}
        
        try:
            # Calculate date to search from
            after_date = datetime.now() - timedelta(hours=hours_back)
            after_timestamp = int(after_date.timestamp())
            
            # Build search query
            # Look for emails FROM the company email address
            query = f"from:{company_email} after:{after_timestamp}"
            
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                logger.info(f"No replies found from {company_email}")
                return {'has_reply': False, 'reply_date': None, 'message_snippet': None}
            
            # Get the most recent message
            latest_message = self.service.users().messages().get(
                userId='me',
                id=messages[0]['id'],
                format='full'
            ).execute()
            
            # Extract information
            headers = latest_message.get('payload', {}).get('headers', [])
            date_header = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
            snippet = latest_message.get('snippet', '')
            
            # Parse date
            reply_date = None
            if date_header:
                try:
                    from email.utils import parsedate_to_datetime
                    reply_date = parsedate_to_datetime(date_header)
                except:
                    reply_date = timezone.now()
            
            logger.info(f"Reply detected from {company_email} on {reply_date}")
            return {
                'has_reply': True,
                'reply_date': reply_date,
                'message_snippet': snippet
            }
            
        except Exception as e:
            logger.error(f"Error checking for replies from {company_email}: {e}")
            return {'has_reply': False, 'reply_date': None, 'message_snippet': None}
    
    def check_multiple_companies(self, companies):
        """
        Check for replies from multiple companies.
        
        Args:
            companies: List of Company objects
        
        Returns:
            dict: {company_id: reply_info}
        """
        results = {}
        
        if not self.service:
            if not self.authenticate():
                return results
        
        for company in companies:
            if not company.email:
                continue
            
            reply_info = self.check_for_replies(company.email)
            if reply_info['has_reply']:
                results[company.id] = reply_info
        
        return results


def test_gmail_authentication():
    """
    Test Gmail API authentication.
    Returns: (success: bool, message: str)
    """
    try:
        detector = GmailReplyDetector()
        success = detector.authenticate()
        
        if success:
            return True, "Gmail API authentication successful!"
        else:
            return False, "Gmail API authentication failed. Check logs for details."
    
    except Exception as e:
        return False, f"Gmail API authentication error: {str(e)}"
