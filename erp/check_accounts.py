import os
import django
import sys

sys.path.append('c:\\Users\\enes3\\erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from email_automation.models import Email, EmailAccount

print(f"Total Accounts: {EmailAccount.objects.count()}")

for acc in EmailAccount.objects.all():
    email_addr = acc.email_address
    user_name = acc.user.username if acc.user else "No User"
    
    total = Email.objects.filter(email_account=acc).count()
    read = Email.objects.filter(email_account=acc, is_read=True).count()
    unread = Email.objects.filter(email_account=acc, is_read=False).count()
    
    inbox_read = Email.objects.filter(email_account=acc, folder='inbox', is_read=True).count()
    
    print(f"User: {user_name} | Email: {email_addr}")
    print(f"  Total: {total} (Read: {read}, Unread: {unread})")
    print(f"  Inbox Read: {inbox_read}")
    
    if inbox_read > 0:
        first_read = Email.objects.filter(email_account=acc, folder='inbox', is_read=True).order_by('-received_at').first()
        print(f"  Newest Read Email: {first_read.subject} (Received: {first_read.received_at})")
