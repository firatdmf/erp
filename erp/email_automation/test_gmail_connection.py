"""
Manual script to test Gmail connection and create EmailAccount
Run this with: python manage.py shell < email_automation/test_gmail_connection.py
"""
from django.contrib.auth import get_user_model
from email_automation.models import EmailAccount

User = get_user_model()

# Get the first user (or specify username)
user = User.objects.first()

if user:
    # Create a test EmailAccount
    email_account, created = EmailAccount.objects.update_or_create(
        user=user,
        defaults={
            'email': 'test@gmail.com',  # This will be replaced during real OAuth
            'access_token': 'dummy_token',
            'refresh_token': 'dummy_refresh_token',
        }
    )
    
    if created:
        print(f"✓ Created test EmailAccount for user: {user.username}")
    else:
        print(f"✓ Updated EmailAccount for user: {user.username}")
    
    print(f"  Email: {email_account.email}")
    print(f"  User: {email_account.user.username}")
else:
    print("✗ No users found in database")

# Show all email accounts
print("\nAll Email Accounts:")
for ea in EmailAccount.objects.all():
    print(f"  - {ea.user.username}: {ea.email}")
