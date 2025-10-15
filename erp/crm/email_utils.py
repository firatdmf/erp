import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_followup_email(company, email_number):
    """
    Send a follow-up email to a company.
    
    Args:
        company: Company model instance
        email_number: Which email in the sequence (1-5)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not company.email:
        logger.warning(f"Cannot send follow-up to {company.name}: No email address")
        return False
    
    if email_number < 1 or email_number > 5:
        logger.error(f"Invalid email number: {email_number}")
        return False
    
    try:
        # Email configuration
        sender_email = getattr(settings, 'FOLLOWUP_EMAIL_FROM', settings.EMAIL_HOST_USER)
        sender_name = getattr(settings, 'FOLLOWUP_SENDER_NAME', 'Nejum ERP Team')
        sender_title = getattr(settings, 'FOLLOWUP_SENDER_TITLE', 'Sales Team')
        sender_company = getattr(settings, 'FOLLOWUP_SENDER_COMPANY', 'Nejum')
        
        # Render email template
        context = {
            'company': company,
            'sender_name': sender_name,
            'sender_title': sender_title,
            'sender_company': sender_company,
        }
        
        template_name = f'crm/emails/followup_{email_number}.html'
        html_content = render_to_string(template_name, context)
        
        # Create email message
        subject = _get_email_subject(email_number, company.name)
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = company.email
        msg['Reply-To'] = sender_email
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email via Gmail SMTP
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Follow-up email {email_number} sent successfully to {company.name} ({company.email})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send follow-up email {email_number} to {company.name}: {str(e)}")
        return False


def _get_email_subject(email_number, company_name):
    """Generate email subject based on email number."""
    subjects = {
        1: f"ERP Solutions for {company_name}",
        2: f"Quick follow-up - {company_name}",
        3: f"Don't want to miss out - {company_name}",
        4: f"Checking in with {company_name}",
        5: f"Final note from Nejum - {company_name}",
    }
    return subjects.get(email_number, f"Follow-up for {company_name}")


def test_email_configuration():
    """
    Test if email configuration is set up correctly.
    Returns tuple: (success: bool, message: str)
    """
    try:
        required_settings = [
            'EMAIL_HOST',
            'EMAIL_PORT',
            'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD',
        ]
        
        missing = []
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                missing.append(setting)
        
        if missing:
            return False, f"Missing email settings: {', '.join(missing)}"
        
        # Try to connect to SMTP server
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        
        return True, "Email configuration is valid and SMTP connection successful"
        
    except Exception as e:
        return False, f"Email configuration test failed: {str(e)}"
