# Gmail API Setup for Automatic Reply Detection

## Overview

This system automatically detects when prospect companies reply to your emails and:
1. ✅ Stops follow-up emails immediately
2. ✅ Creates a task in your todo list to "Reply back"

## Setup Steps

### Step 1: Enable Gmail API in Google Cloud

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/

2. **Create a New Project** (or use existing)
   - Click "Select a project" → "New Project"
   - Name: "ERP Gmail Integration"
   - Click "Create"

3. **Enable Gmail API**
   - In the search bar, search for "Gmail API"
   - Click on "Gmail API"
   - Click "Enable"

### Step 2: Create OAuth Credentials

1. **Go to Credentials Page**
   - Left menu: APIs & Services → Credentials
   - Or visit: https://console.cloud.google.com/apis/credentials

2. **Configure OAuth Consent Screen**
   - Click "OAuth consent screen" tab
   - Select "External" (unless you have Google Workspace)
   - Click "Create"
   
   **Fill in required fields:**
   - App name: "Nejum ERP"
   - User support email: your-email@gmail.com
   - Developer contact: your-email@gmail.com
   - Click "Save and Continue"
   
   **Scopes:**
   - Click "Add or Remove Scopes"
   - Search for "Gmail API"
   - Select: `https://www.googleapis.com/auth/gmail.readonly`
   - Click "Update" → "Save and Continue"
   
   **Test users:**
   - Click "Add Users"
   - Add your Gmail address: your-email@gmail.com
   - Click "Save and Continue"

3. **Create OAuth Client ID**
   - Go back to "Credentials" tab
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Name: "ERP Gmail Client"
   - Click "Create"

4. **Download Credentials**
   - Click the download icon (⬇️) next to your newly created OAuth client
   - Save the JSON file

### Step 3: Install Credentials in Your Project

1. **Rename and move the downloaded JSON file:**
   ```bash
   cd /Users/muhammed/Code/erp
   # Move your downloaded file (usually in ~/Downloads)
   mv ~/Downloads/client_secret_*.json gmail_credentials.json
   ```

2. **Verify file location:**
   ```bash
   ls -la gmail_credentials.json
   # Should show the file exists
   ```

### Step 4: Install Required Python Packages

```bash
cd /Users/muhammed/Code/erp
/Users/muhammed/Code/erp/vir_env/bin/pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Step 5: Authenticate with Gmail

Run the authentication command:

```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py shell
```

Then in the Python shell:
```python
from crm.gmail_service import test_gmail_authentication
success, message = test_gmail_authentication()
print(message)
```

**What happens:**
1. A browser window will open
2. Sign in with your Gmail account
3. Click "Allow" to grant permissions
4. Browser will show "Authentication successful"
5. Token is saved to `gmail_token.pickle`

### Step 6: Test Reply Detection

```bash
# Check for replies in the last 24 hours
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py check_email_replies --hours-back 24
```

### Step 7: Set Up Automatic Checking (Cron)

Add to your crontab to check for replies every hour:

```bash
crontab -e

# Add these lines:
# Check for follow-up emails to send (daily at 9 AM)
0 9 * * * /Users/muhammed/Code/erp/vir_env/bin/python /Users/muhammed/Code/erp/erp/manage.py send_followup_emails >> /Users/muhammed/Code/erp/followup_emails.log 2>&1

# Check for replies every hour
0 * * * * /Users/muhammed/Code/erp/vir_env/bin/python /Users/muhammed/Code/erp/erp/manage.py check_email_replies --hours-back 24 >> /Users/muhammed/Code/erp/reply_check.log 2>&1
```

---

## How It Works

### When a Company Replies

1. **Reply Detection**
   - System checks Gmail inbox every hour (via cron)
   - Looks for emails FROM prospect company addresses
   - Searches messages from the last 24 hours

2. **Automatic Actions**
   - ✅ Stops follow-up emails immediately
   - ✅ Marks follow-up as inactive
   - ✅ Sets `stopped_reason = "reply_received"`
   - ✅ Creates a task: "Reply back to [Company Name]"

3. **Task Created**
   - **Name**: "Reply back to [Company Name]"
   - **Description**: Includes reply date and preview
   - **Due Date**: Tomorrow
   - **Linked to**: The company
   - Shows in your todo list

### Viewing Tasks

Go to your todo list in the admin panel:
```
http://your-domain/admin/todo/task/
```

Or access via your todo module interface.

---

## Commands

### Check for Replies
```bash
# Check last 24 hours (default)
python erp/manage.py check_email_replies

# Check last 48 hours
python erp/manage.py check_email_replies --hours-back 48

# Check specific company
python erp/manage.py check_email_replies --company-id 123
```

### Test Gmail Authentication
```bash
python erp/manage.py shell
>>> from crm.gmail_service import test_gmail_authentication
>>> success, message = test_gmail_authentication()
>>> print(message)
```

### Send Follow-ups (Existing Command)
```bash
python erp/manage.py send_followup_emails
```

---

## Troubleshooting

### "Failed to authenticate with Gmail API"

**Solution 1: Re-authenticate**
```bash
# Delete the token file
rm gmail_token.pickle

# Re-run authentication
python erp/manage.py shell
>>> from crm.gmail_service import test_gmail_authentication
>>> test_gmail_authentication()
```

**Solution 2: Check credentials file**
```bash
# Make sure file exists
ls -la gmail_credentials.json

# Should show the JSON file
```

### "Gmail credentials file not found"

Make sure `gmail_credentials.json` is in the project root:
```
/Users/muhammed/Code/erp/gmail_credentials.json
```

### "Access blocked: This app's request is invalid"

- Go back to Google Cloud Console
- Make sure OAuth consent screen is configured
- Add your email as a test user
- Make sure Gmail API is enabled

### "No replies found" (but you know there are replies)

1. Check the company email address is correct
2. Increase `--hours-back` parameter
3. Check Gmail search manually: `from:company@example.com`
4. Make sure follow-up is active (not already stopped)

### Token Expired

The token auto-refreshes. If issues persist:
```bash
rm gmail_token.pickle
# Re-authenticate
```

---

## Security Notes

1. **Keep credentials secure**
   - `gmail_credentials.json` - OAuth credentials (DO NOT commit)
   - `gmail_token.pickle` - Access token (DO NOT commit)
   - Add to `.gitignore`:
     ```
     gmail_credentials.json
     gmail_token.pickle
     ```

2. **Permissions**
   - System only has **read-only** access to Gmail
   - Cannot send emails via API (uses SMTP instead)
   - Cannot delete or modify emails

3. **Token Storage**
   - Token stored locally in `gmail_token.pickle`
   - Auto-refreshes when expired
   - Revoke access anytime at: https://myaccount.google.com/permissions

---

## Testing the System

### Test 1: Send yourself a test email

1. Add a test company with your own email
2. Wait for Email 1 to be sent
3. Reply to that email from your inbox
4. Run: `python erp/manage.py check_email_replies`
5. Check that:
   - Follow-ups stopped
   - Task created in todo list

### Test 2: Check existing companies

```bash
# Test with FIRAT AS (if added)
python erp/manage.py check_email_replies --company-id 1
```

---

## Complete Workflow

```
1. Add prospect company
   ↓
2. Email 1 sent immediately
   ↓
3. Company replies
   ↓
4. Hourly cron job runs check_email_replies
   ↓
5. Reply detected!
   ↓
6. Actions:
   - Stop follow-ups ✓
   - Create "Reply back" task ✓
   ↓
7. You see task in todo list
   ↓
8. Reply to company
   ↓
9. Mark task as complete
```

---

## Files Created

- `erp/crm/gmail_service.py` - Gmail API integration
- `erp/crm/management/commands/check_email_replies.py` - Reply checking command
- `gmail_credentials.json` - OAuth credentials (you provide)
- `gmail_token.pickle` - Access token (auto-generated)

---

**Need Help?** Check the logs:
- Follow-up log: `/Users/muhammed/Code/erp/followup_emails.log`
- Reply check log: `/Users/muhammed/Code/erp/reply_check.log`
