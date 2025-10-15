# Follow-Up Email System - Quick Start

## What You Need

1. **Gmail App Password** - Generate from Google Account settings
2. **Environment variables** in `erp/.env`:
   ```
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   ```

## How to Use

### Test the System (Dry Run)
```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails --dry-run
```

### Send Actual Follow-ups
```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails
```

### Set Up Automatic Daily Runs
```bash
crontab -e
# Add this line:
0 9 * * * /Users/muhammed/Code/erp/vir_env/bin/python /Users/muhammed/Code/erp/erp/manage.py send_followup_emails >> /Users/muhammed/Code/erp/followup_emails.log 2>&1
```

## Email Schedule
- Day 3: Email 1
- Day 10: Email 2
- Day 24: Email 3
- Day 54: Email 4
- Day 114: Email 5 (final)

## What Happens Automatically

✅ **When you add a prospect company** (with email):
- Follow-up tracking starts automatically

✅ **When status changes** from "prospect":
- Follow-ups stop automatically

✅ **After 5 emails**:
- System stops and notifies you

## Admin Panel

View/manage follow-ups at: `/admin/crm/companyfollowup/`

## Full Documentation

See `FOLLOWUP_EMAIL_SETUP.md` for complete setup instructions and troubleshooting.
