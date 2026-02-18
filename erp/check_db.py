import os
import django
import sys

# Add project root to path
sys.path.append('c:\\Users\\enes3\\erp')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from email_automation.models import Email, EmailAccount
from django.contrib.auth import get_user_model

print("--- Checking Email Accounts ---")
for acc in EmailAccount.objects.all():
    count = Email.objects.filter(email_account=acc).count()
    read = Email.objects.filter(email_account=acc, is_read=True).count()
    unread = Email.objects.filter(email_account=acc, is_read=False).count()
    print(f"User: {acc.user.username} (ID: {acc.user.id})")
    print(f"  Account: {acc.email_address}")
    print(f"  Total Emails: {count}")
    print(f"  Read: {read}")
    print(f"  Unread: {unread}")
    
    # Check if any read emails are visible in 'inbox' folder
    inbox_read = Email.objects.filter(email_account=acc, folder='inbox', is_read=True).count()
    print(f"  Inbox Read Emails: {inbox_read}")
    
    # Check for null received_at
    null_received = Email.objects.filter(email_account=acc, received_at__isnull=True).count()
    print(f"  Null received_at: {null_received}")
print("-------------------------------")
