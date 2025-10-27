# 📧 Automated Follow-Up Email System

## Quick Overview

This system automatically sends 5 follow-up emails to prospect companies at scheduled intervals via your Gmail account. It handles everything automatically - starting, sending, and stopping based on your company status changes.

## ⚡ Quick Start (3 Steps)

### 1. Get Gmail App Password
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to "App passwords" → Create new → Copy the 16-character password

### 2. Add to Your `.env` File
```bash
# In erp/.env, add:
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-character-app-password
```

### 3. Test It
```bash
# See what would be sent (no actual emails)
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails --dry-run
```

✅ That's it! You're ready to go.

## 📅 Email Schedule

| Email | Days After | Cumulative Days |
|-------|-----------|-----------------|
| #1    | Immediate | Day 0 (when you save the company) |
| #2    | 3 days    | Day 3           |
| #3    | 7 days    | Day 10          |
| #4    | 14 days   | Day 24          |
| #5    | 30 days   | Day 54 (Final)  |

## 🤖 What Happens Automatically

### ✅ When You Add a Company
- If `status = "prospect"` AND has email → **Email 1 sent immediately!**
- Follow-up tracking starts for remaining 4 emails

### ✅ When You Change Status
- Change from "prospect" to anything else → Follow-ups stop immediately

### ✅ When Reply Received
- Just change company status → System stops automatically

### ✅ After 5 Emails
- System stops and shows notification

## 🎯 Daily Usage

### Check What's Due (Dry Run - No Emails Sent)
```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails --dry-run
```

### Send Due Follow-Ups
```bash
/Users/muhammed/Code/erp/vir_env/bin/python erp/manage.py send_followup_emails
```

### Set Up Auto-Run (Once)
```bash
crontab -e
# Paste this line:
0 9 * * * /Users/muhammed/Code/erp/vir_env/bin/python /Users/muhammed/Code/erp/erp/manage.py send_followup_emails >> /Users/muhammed/Code/erp/followup_emails.log 2>&1
```
This runs every day at 9 AM.

## 👀 Monitor in Admin Panel

1. Go to: `http://your-domain/admin/crm/companyfollowup/`
2. See all active follow-ups
3. Check email counts
4. Manually stop if needed

## 📝 Customize Email Content

Edit templates in: `erp/crm/templates/crm/emails/`
- `followup_1.html` through `followup_5.html`

Available variables:
- `{{ company.name }}`
- `{{ sender_name }}`
- `{{ sender_title }}`
- `{{ sender_company }}`

## 🛠️ Files Created

```
erp/crm/
├── models.py           (Added CompanyFollowUp model)
├── signals.py          (Auto start/stop logic)
├── email_utils.py      (Email sending)
├── admin.py            (Admin panel integration)
├── templates/crm/emails/
│   ├── followup_1.html
│   ├── followup_2.html
│   ├── followup_3.html
│   ├── followup_4.html
│   └── followup_5.html
└── management/commands/
    └── send_followup_emails.py

Documentation:
├── FOLLOWUP_EMAIL_SETUP.md      (Complete guide)
├── FOLLOWUP_QUICKSTART.md       (Quick reference)
├── IMPLEMENTATION_SUMMARY.md    (Technical details)
└── README_FOLLOWUP_SYSTEM.md    (This file)
```

## 🐛 Troubleshooting

### "Gmail blocking sign-in"
→ Use App Password (not your regular password)

### "No emails being sent"
→ Run with `--dry-run` to see what would be sent
→ Check company still has status="prospect"
→ Check company has email address

### "How to stop follow-ups manually"
→ Go to admin: `/admin/crm/companyfollowup/`
→ Uncheck "Is active" for that company

## 📚 Full Documentation

- **Complete Setup Guide**: `FOLLOWUP_EMAIL_SETUP.md`
- **Quick Reference**: `FOLLOWUP_QUICKSTART.md`
- **Technical Details**: `IMPLEMENTATION_SUMMARY.md`

## ✨ Key Features

- ✅ Fully automated - set it and forget it
- ✅ Smart stopping on status changes
- ✅ Professional HTML email templates
- ✅ Dry-run testing mode
- ✅ Detailed admin panel
- ✅ Error handling and logging
- ✅ Gmail SMTP integration
- ✅ Notifications when sequences complete

---

**Need Help?** Check `FOLLOWUP_EMAIL_SETUP.md` for detailed troubleshooting and setup instructions.
