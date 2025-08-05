# Email Configuration Guide

To enable email notifications for your automated calendar sync, you need to set up the following environment variables:

## Required Environment Variables

Add these to your `.env` file or set them in your deployment environment:

```bash
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
TO_EMAIL=recipient@example.com

# Sync Configuration
SEND_EMAIL=true
USE_GEMINI=true
```

## Gmail Setup Instructions

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
   - Use this password as `SMTP_PASSWORD`

## Alternative Email Providers

### Outlook/Hotmail
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

### Yahoo
```bash
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
```

### Custom SMTP Server
```bash
SMTP_SERVER=your-smtp-server.com
SMTP_PORT=587
```

## Email Notification Settings

- `SEND_EMAIL=true` - Enable/disable email notifications
- `USE_GEMINI=true` - Use Gemini parser (true) or traditional parser (false)
- `TO_EMAIL` - Email address to receive notifications

## Email Content

The automated sync will send HTML emails with:
- Summary of changes (created, updated, deleted events)
- Detailed breakdown by sheet
- Error reports if any issues occur
- Success rate and statistics

## Testing Email Configuration

You can test the email configuration by running:

```bash
python automated_sync.py
```

This will run the sync and send an email if changes are detected or errors occur. 