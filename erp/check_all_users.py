import os
import django
import sys
from django.db.models import Count

sys.path.append('c:\\Users\\enes3\\erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.contrib.auth import get_user_model
from email_automation.models import Email, EmailAccount

User = get_user_model()
print(f"Total Users: {User.objects.count()}")

for u in User.objects.all():
    print(f"User: {u.username} (ID: {u.id})")
    acc = EmailAccount.objects.filter(user=u).first()
    if acc:
        count = Email.objects.filter(email_account=acc).count()
        read = Email.objects.filter(email_account=acc, is_read=True).count()
        unread = Email.objects.filter(email_account=acc, is_read=False).count()
        print(f"  Account: {acc.email_address} | Total: {count} (R:{read}/U:{unread})")
        
        folders = Email.objects.filter(email_account=acc).values('folder').annotate(c=Count('id'))
        print(f"  Folders: {list(folders)}")
    else:
        print("  No EmailAccount")
