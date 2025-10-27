# Testing the Immediate Email Feature

## Quick Test Guide

### Prerequisites
Make sure you've set up Gmail credentials in `erp/.env`:
```bash
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## Test 1: Verify Email Configuration

```bash
cd /Users/muhammed/Code/erp
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py shell
```

In the Python shell:
```python
from crm.email_utils import test_email_configuration
success, message = test_email_configuration()
print(message)
exit()
```

Expected output: `Email configuration is valid and SMTP connection successful`

---

## Test 2: Create Test Company and Verify Immediate Email

### Step 1: Start Django Server
```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py runserver
```

### Step 2: Go to Admin Panel
1. Open browser: `http://127.0.0.1:8000/admin/`
2. Login with your admin credentials
3. Go to **CRM > Companies**

### Step 3: Add New Prospect Company
Click "Add Company" and fill in:
- **Name**: Test Company ABC
- **Email**: your-test-email@gmail.com (use your own email to receive it)
- **Status**: Prospect (default)
- Click **Save**

### Step 4: Check Your Email
- Check the email address you entered
- You should receive Email 1 immediately (within seconds)
- Subject: "ERP Solutions for Test Company ABC"

### Step 5: Verify in Admin Panel
1. Go to **CRM > Company Follow Ups**
2. Find "Test Company ABC"
3. Verify:
   - ✅ `is_active`: True
   - ✅ `emails_sent_count`: 1
   - ✅ `last_email_sent_at`: Shows current timestamp

---

## Test 3: Verify Follow-Up Schedule

### Check What Would Be Sent Next
```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails --dry-run
```

Expected output:
```
Running in DRY RUN mode - no emails will be sent
Checking 1 active follow-ups...
(No emails due yet - Email 2 will be sent in 3 days)
```

---

## Test 4: Test Status Change Stops Follow-Ups

### Step 1: Change Company Status
1. Go to **CRM > Companies**
2. Click on "Test Company ABC"
3. Change **Status** from "Prospect" to "Qualified"
4. Click **Save**

### Step 2: Verify Follow-Ups Stopped
1. Go to **CRM > Company Follow Ups**
2. Find "Test Company ABC"
3. Verify:
   - ✅ `is_active`: False
   - ✅ `stopped_reason`: "status_changed"
   - ✅ `stopped_at`: Shows current timestamp

---

## Test 5: Test Error Handling (Email Fails)

### Temporarily Break Email Config
```bash
# Edit erp/.env
# Change EMAIL_HOST_PASSWORD to something wrong
EMAIL_HOST_PASSWORD=wrongpassword
```

### Add Another Test Company
1. Go to **CRM > Companies**
2. Add new company: "Test Company XYZ"
3. Click **Save**

### Check Results
- Company should still save successfully ✅
- Check Django logs for error message
- Go to **CRM > Company Follow Ups**
- "Test Company XYZ" will have `emails_sent_count = 0` (email failed)

### Fix It
```bash
# Restore correct password in erp/.env
EMAIL_HOST_PASSWORD=your-correct-app-password
```

---

## Test 6: Test Dry Run Before Real Send

```bash
# See what would be sent without actually sending
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails --dry-run --company-id 1
```

Replace `1` with actual company ID from admin panel.

---

## Expected Behavior Summary

✅ **When company is saved:**
- Email 1 sent immediately
- Follow-up tracking created with count = 1
- No errors in console

✅ **When status changes:**
- Follow-ups stop automatically
- `is_active` becomes False
- `stopped_reason` = "status_changed"

✅ **When email fails:**
- Company still saves
- Error logged
- `emails_sent_count` = 0

---

## Troubleshooting

### Email Not Received
1. Check spam folder
2. Verify email address is correct
3. Test email configuration (Test 1)
4. Check Django logs for errors

### Company Saved But No Follow-Up Record
- Check company has status = "prospect"
- Check company has email address
- Verify signals are loaded (check `erp/crm/apps.py`)

### Error: "No module named 'crm.email_utils'"
- Make sure you're using the virtual environment
- Restart Django server

---

## Clean Up Test Data

After testing, you can delete test companies:

```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py shell
```

```python
from crm.models import Company
Company.objects.filter(name__startswith="Test Company").delete()
exit()
```

---

**Next Step:** Once testing is complete, set up the cron job for automatic daily follow-ups 2-5!
