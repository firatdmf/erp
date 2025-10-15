# Automated Follow-Up Email System - Setup & Usage

This document describes the automated follow-up email system for prospect companies in the Nejum ERP CRM module.

## Overview

When a company is added with `status="prospect"`, the system automatically:
1. Creates a follow-up tracking record
2. Schedules 5 follow-up emails at specific intervals
3. Stops automatically if the status changes or after 5 emails
4. Notifies you when the sequence completes

## Email Schedule

- **Email 1**: 3 days after company creation
- **Email 2**: 7 days after Email 1 (10 days total)
- **Email 3**: 14 days after Email 2 (24 days total)  
- **Email 4**: 30 days after Email 3 (54 days total)
- **Email 5**: 60 days after Email 4 (114 days total)

## Setup Instructions

### 1. Gmail Configuration

You need to set up Gmail SMTP access. For best results, use a Gmail "App Password":

1. Go to your Google Account settings
2. Navigate to Security > 2-Step Verification (enable if not enabled)
3. At the bottom, select "App passwords"
4. Generate a new app password for "Mail"
5. Copy the 16-character password

### 2. Environment Variables

Add these variables to your `erp/.env` file:

```bash
# Email Configuration
EMAIL_HOST_USER=your-gmail-address@gmail.com
EMAIL_HOST_PASSWORD=your-16-character-app-password

# Optional: Customize sender information
FOLLOWUP_EMAIL_FROM=your-gmail-address@gmail.com
FOLLOWUP_SENDER_NAME=Your Name
FOLLOWUP_SENDER_TITLE=Your Title
FOLLOWUP_SENDER_COMPANY=Your Company Name
```

### 3. Test Email Configuration

Run this command to test your email setup:

```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py shell
```

Then in the Python shell:

```python
from crm.email_utils import test_email_configuration
success, message = test_email_configuration()
print(message)
```

### 4. Set Up Cron Job

To run the follow-up system automatically, add a cron job:

```bash
# Edit your crontab
crontab -e

# Add this line to run daily at 9 AM
0 9 * * * /Users/muhammed/Code/erp/vir_env/bin/python /Users/muhammed/Code/erp/erp/manage.py send_followup_emails >> /Users/muhammed/Code/erp/followup_emails.log 2>&1
```

Or run it manually when needed (see Usage section below).

## Usage

### Manual Command Execution

#### Send follow-ups (production mode):
```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails
```

#### Dry run (test without sending emails):
```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails --dry-run
```

#### Test with specific company:
```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails --company-id 123
```

### How It Works

1. **When you add a new company with status="prospect"**:
   - A `CompanyFollowUp` record is automatically created
   - The system tracks this company for follow-up emails

2. **When the management command runs**:
   - Checks all active follow-ups
   - Sends emails that are due based on the schedule
   - Updates tracking information
   - Stops follow-ups when conditions are met

3. **Follow-ups stop automatically when**:
   - Status changes from "prospect" to anything else (e.g., "qualified")
   - 5 emails have been sent (max limit reached)
   - You manually stop them in the admin panel

4. **Notifications**:
   - The command output shows which companies reached the 5-email limit
   - You'll be notified to consider manual outreach for these companies

### Monitoring in Admin Panel

1. Go to Django admin: `/admin/`
2. Navigate to: **CRM > Company Follow Ups**
3. You can see:
   - Active follow-up sequences
   - Number of emails sent per company
   - When the last email was sent
   - Why follow-ups stopped (if stopped)

### Manually Stopping Follow-ups

To stop follow-ups for a company without changing their status:

**Option 1: Admin Panel**
1. Go to **CRM > Company Follow Ups**
2. Find the company's follow-up record
3. Uncheck "Is active"
4. Add a reason in "Stopped reason" (e.g., "manual_stop")
5. Save

**Option 2: Django Shell**
```python
from crm.models import Company
company = Company.objects.get(name="Company Name")
company.followup.stop_followups(reason="manual_stop")
```

### Handling Replies

When a company replies to your email:
- Change their status from "prospect" to "qualified" (or another status)
- The system will automatically stop sending follow-ups via the signal handler

## Email Templates

Email templates are located in: `erp/crm/templates/crm/emails/`

To customize the email content:
1. Edit files: `followup_1.html` through `followup_5.html`
2. Variables available in templates:
   - `{{ company.name }}` - Company name
   - `{{ sender_name }}` - Your name (from settings)
   - `{{ sender_title }}` - Your title
   - `{{ sender_company }}` - Your company name

## Troubleshooting

### Emails not sending?

1. **Check email configuration**:
   ```bash
   /Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py shell
   >>> from crm.email_utils import test_email_configuration
   >>> success, message = test_email_configuration()
   >>> print(message)
   ```

2. **Check company has email address**:
   - Follow-ups only work for companies with email addresses

3. **Check follow-up is active**:
   - Go to admin panel and verify `is_active=True`

4. **Run dry-run to see what would be sent**:
   ```bash
   /Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails --dry-run
   ```

5. **Check logs**:
   - If running via cron, check the log file: `/Users/muhammed/Code/erp/followup_emails.log`
   - Look for error messages in Django logs

### Common Issues

**"Gmail blocking sign-in attempts"**
- Solution: Use App Password (see Gmail Configuration section)
- Make sure 2-Step Verification is enabled

**"No emails being sent"**
- Verify cron job is running: `crontab -l`
- Check that enough time has passed per the schedule
- Verify company status is still "prospect"

**"Follow-up not created for new company"**
- Make sure the company has an email address
- Check that signals are loaded (should happen automatically)
- Verify status is set to "prospect" on creation

## Database Models

### CompanyFollowUp Model

Fields:
- `company`: OneToOne relationship to Company
- `is_active`: Whether follow-ups are currently active
- `emails_sent_count`: Number of emails sent (0-5)
- `last_email_sent_at`: Timestamp of last email
- `stopped_reason`: Why follow-ups stopped (if applicable)
- `stopped_at`: When follow-ups were stopped

## Security Notes

1. **Never commit your `.env` file** - It contains your email credentials
2. **Use App Passwords** - Don't use your main Gmail password
3. **Monitor email sending** - Keep track of emails sent to avoid spam complaints
4. **Respect email limits** - Gmail has daily sending limits (500-2000 emails/day depending on account type)

## Support

For issues or questions:
1. Check this documentation
2. Review the code in `erp/crm/`:
   - `models.py` - CompanyFollowUp model
   - `signals.py` - Automatic follow-up creation/stopping
   - `email_utils.py` - Email sending logic
   - `management/commands/send_followup_emails.py` - Main command
3. Check Django logs for errors
