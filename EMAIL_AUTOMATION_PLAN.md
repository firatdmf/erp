# Email Automation System - Implementation Plan

## Overview
Otomatik email sistemi - Prospect company'lere 6 email'lik bir sequence gönderir, cevap gelirse otomatik durdurur ve company status'ü qualified yapar.

## Database Models ✅ (COMPLETED)

### EmailAccount
- Gmail hesabı bağlantısı
- OAuth tokens (access, refresh)
- User başına 1 email hesabı

### EmailTemplate
- 6 adet email template (sequence 1-6)
- Subject + Body (placeholders: {{company_name}}, {{contact_name}})
- days_after_previous: Bir önceki emailden kaç gün sonra gönderilecek

### EmailCampaign
- Her company için 1 campaign
- Status: active/paused/completed/stopped
- emails_sent: Kaç email gönderildi (max 6)
- reply_received: Cevap geldi mi?
- next_email_scheduled_at: Sonraki email ne zaman gönderilecek

### SentEmail
- Gönderilen her email kaydı
- Gmail message_id + thread_id
- opened, replied tracking

### ReceivedEmail  
- Gelen emailler (inbox)
- Campaign ile ilişkilendirme
- Reply detection

## Next Steps

### 1. Settings Configuration (URGENT - Öncelik 1)
**Dosya:** `erp/settings.py`
```python
INSTALLED_APPS += ['email_automation']

# Gmail OAuth Settings
GMAIL_CLIENT_ID = 'your-client-id'
GMAIL_CLIENT_SECRET = 'your-client-secret'
GMAIL_REDIRECT_URI = 'http://localhost:8000/email/oauth2callback/'
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]
```

### 2. Run Migrations
```bash
python manage.py makemigrations email_automation
python manage.py migrate
```

### 3. Gmail OAuth Integration (Öncelik 2)
**Dosyalar:**
- `email_automation/gmail_service.py` - Gmail API wrapper
- `email_automation/views.py` - OAuth flow views

**Views needed:**
- `connect_gmail()` - Start OAuth flow
- `oauth2callback()` - Handle OAuth callback
- `disconnect_gmail()` - Remove connection

### 4. Email Dashboard (Öncelik 3)
**Dosya:** `email_automation/templates/email_automation/dashboard.html`

**Sections:**
- Gmail connection status
- Active campaigns count
- Total emails sent
- Campaign list with progress (Company, Emails Sent, Status, Next Email)

### 5. Inbox/Outbox Views (Öncelik 4)
**Views:**
- `inbox_view()` - Show received emails
- `outbox_view()` - Show sent emails
- `email_detail()` - Show single email detail

### 6. Email Templates Management (Öncelik 5)
**Views:**
- `template_list()` - List all 6 templates
- `template_edit()` - Edit template
- Default templates creation command

### 7. Automatic Email Sending (Öncelik 6)
**Dosya:** `email_automation/tasks.py`

**Tasks:**
- `send_scheduled_emails()` - Check campaigns and send emails
- `check_for_replies()` - Poll Gmail for new replies
- `process_reply()` - Mark reply, update status

**Setup:** Celery or cron job to run every hour

### 8. Sidebar Menu Integration (Öncelik 7)
**Dosya:** `erp/templates/base.html`

Add to navigation:
```html
<li class="nav-item">
  <a href="{% url 'email:dashboard' %}" class="nav-link">
    <i class="fa fa-envelope fa-2x"></i>
    <span class="link-text">Mail</span>
  </a>
</li>
```

### 9. URLs Configuration
**Dosya:** `email_automation/urls.py`
```python
app_name = 'email'
urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('connect/', connect_gmail, name='connect_gmail'),
    path('oauth2callback/', oauth2callback, name='oauth2callback'),
    path('disconnect/', disconnect_gmail, name='disconnect'),
    path('inbox/', inbox_view, name='inbox'),
    path('outbox/', outbox_view, name='outbox'),
    path('templates/', template_list, name='templates'),
    path('campaigns/', campaign_list, name='campaigns'),
]
```

**Main urls.py:**
```python
path('email/', include('email_automation.urls')),
```

## Gmail API Setup Requirements

### Google Cloud Console Steps:
1. Create project at console.cloud.google.com
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Add redirect URI: http://localhost:8000/email/oauth2callback/
5. Download credentials JSON

### Environment Variables:
```
GMAIL_CLIENT_ID=xxx
GMAIL_CLIENT_SECRET=xxx
```

## Installation Requirements
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## Features Summary

### ✅ What Works (After Implementation):
1. Gmail OAuth connection
2. 6-email sequence templates
3. Automatic campaign creation for prospect companies
4. Scheduled email sending (respects timing rules)
5. Reply detection
6. Auto status change: prospect → qualified
7. Campaign stop on reply
8. Inbox/Outbox views
9. Campaign dashboard with progress tracking

### 🔄 Email Flow:
1. Company created with status="prospect" → EmailCampaign created
2. Email 1 sent immediately (or after X days)
3. Email 2-6 sent based on days_after_previous
4. If reply received → campaign stops, status → qualified
5. If no reply after 6 emails → campaign completed

### 📧 Email Content:
Templates support placeholders:
- `{{company_name}}` - Company.name
- `{{contact_name}}` - Contact.name (first contact from company)
- More placeholders can be added as needed

## Current Status
- ✅ Models created
- ⏳ Migrations pending
- ⏳ Views pending
- ⏳ Templates pending
- ⏳ Gmail integration pending
- ⏳ Celery tasks pending
- ⏳ UI integration pending
