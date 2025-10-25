"""
Background scheduler for automatic email sending using APScheduler
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import atexit

logger = logging.getLogger(__name__)

scheduler = None


def send_scheduled_emails_job():
    """Job that processes scheduled campaigns"""
    try:
        from .email_service import process_scheduled_campaigns
        sent_count = process_scheduled_campaigns()
        if sent_count > 0:
            logger.info(f"✓ Background: Sent {sent_count} scheduled emails")
            print(f"✓ Background: Sent {sent_count} scheduled emails")
    except Exception as e:
        logger.error(f"✗ Background: Error in scheduled email job: {str(e)}")
        print(f"✗ Background: Error in scheduled email job: {str(e)}")


def check_replies_job():
    """Job that checks for replies to campaign emails"""
    try:
        from .models import EmailAccount
        from .gmail_utils import check_campaigns_for_replies
        
        # Check all active email accounts
        email_accounts = EmailAccount.objects.filter(is_active=True)
        
        total_replies = 0
        for account in email_accounts:
            reply_count = check_campaigns_for_replies(account)
            total_replies += reply_count
        
        if total_replies > 0:
            logger.info(f"✓ Background: Detected {total_replies} new replies")
            print(f"✓ Background: Detected {total_replies} new replies")
    except Exception as e:
        logger.error(f"✗ Background: Error in reply detection job: {str(e)}")
        print(f"✗ Background: Error in reply detection job: {str(e)}")


def start_scheduler():
    """Start the APScheduler background scheduler"""
    global scheduler
    
    if scheduler is not None:
        return
    
    scheduler = BackgroundScheduler()
    
    # Add job to send scheduled emails every 1 minute
    # Change to minutes=5 for production
    scheduler.add_job(
        func=send_scheduled_emails_job,
        trigger=IntervalTrigger(minutes=1),
        id='email_campaign_job',
        name='Process scheduled email campaigns',
        replace_existing=True
    )
    
    # Add job to check for replies every 5 minutes
    # Change to minutes=10 or 15 for production to reduce API calls
    scheduler.add_job(
        func=check_replies_job,
        trigger=IntervalTrigger(minutes=5),
        id='reply_detection_job',
        name='Check campaigns for replies',
        replace_existing=True
    )
    
    scheduler.start()
    print("✓ APScheduler started")
    print("  - Email sending: every 1 minute")
    print("  - Reply detection: every 5 minutes")
    logger.info("✓ APScheduler started with email sending and reply detection")
    
    # Shut down scheduler when app exits
    atexit.register(lambda: scheduler.shutdown())


def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        print("✓ Email scheduler stopped")
        logger.info("✓ Email scheduler stopped")
