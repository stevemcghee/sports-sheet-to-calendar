# Gmail Account Setup Guide

This guide helps you set up the calendar sync app for regular Gmail accounts without domain-wide delegation.

## Overview

- **Deployment Account**: `smcghee@gmail.com` (runs the app)
- **Calendar Owner**: `sloswimtiming@gmail.com` (owns the calendars)
- **Authentication**: OAuth2 with calendar sharing

## Step 1: Set Up OAuth2 Credentials

### 1.1 Create OAuth2 Client ID

1. Go to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Application type: "Web application"
4. Add authorized redirect URIs:
   - `http://localhost:5000/auth/callback` (for local testing)
   - `https://your-cloud-run-url/auth/callback` (after deployment)
5. Add test users:
   - `smcghee@gmail.com`
   - `sloswimtiming@gmail.com`

### 1.2 Download Credentials

1. Click "Download JSON" to get your OAuth2 credentials
2. Save as `credentials.json` in your project directory

## Step 2: Share Calendars

### 2.1 Share from sloswimtiming@gmail.com

For each calendar that needs to be synced:

1. Go to [Google Calendar](https://calendar.google.com)
2. Sign in as `sloswimtiming@gmail.com`
3. Right-click on the calendar name
4. Select "Settings and sharing"
5. Scroll to "Share with specific people"
6. Click "Add people"
7. Add `smcghee@gmail.com`
8. Set permission to "Make changes to events"
9. Click "Send"

### 2.2 Get Calendar IDs

1. In Google Calendar, right-click on each calendar
2. Select "Settings and sharing"
3. Scroll down to "Integrate calendar"
4. Copy the "Calendar ID" (looks like: `sloswimtiming@gmail.com` or `abc123@group.calendar.google.com`)

## Step 3: Deploy the Application

Run the deployment script:

```bash
chmod +x deploy_simple_gmail.sh
./deploy_simple_gmail.sh
```

## Step 4: Set Environment Variables

In Cloud Run console, add these environment variables:

```
SPREADSHEET_ID=your-spreadsheet-id
GEMINI_API_KEY=your-gemini-api-key
FLASK_SECRET_KEY=your-secret-key
SEND_EMAIL=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sloswimtiming@gmail.com
SMTP_PASSWORD=your-app-password
TO_EMAIL=sloswimtiming@gmail.com
```

## Step 5: Test the Setup

### 5.1 Test Authentication

1. Visit your Cloud Run URL
2. Click "Authenticate with Google"
3. Sign in as `smcghee@gmail.com`
4. Grant permissions to access `sloswimtiming@gmail.com`'s calendars

### 5.2 Test Calendar Access

1. Go to your Cloud Run URL
2. Click "Load Sheet" to test spreadsheet access
3. Click "Apply Changes" to test calendar access

## Step 6: Monitor the System

### 6.1 Cloud Run Logs

- Go to [Cloud Run Console](https://console.cloud.google.com/run)
- Find your service and click "Logs"

### 6.2 Scheduler Logs

```bash
gcloud scheduler jobs logs calendar-sync-job
```

### 6.3 Email Notifications

Check `sloswimtiming@gmail.com` for daily reports

## Troubleshooting

### Permission Denied Errors

If you get permission errors:

1. **Check Calendar Sharing**: Verify `sloswimtiming@gmail.com` has shared the calendars
2. **Check OAuth2 Setup**: Ensure OAuth2 credentials are configured correctly
3. **Check Test Users**: Verify both emails are added as test users

### Authentication Issues

If authentication fails:

1. **Clear Browser Cookies**: Clear cookies for Google
2. **Check Redirect URIs**: Ensure Cloud Run URL is in authorized redirect URIs
3. **Check Test Users**: Verify both emails are in test users list

### API Quota Issues

If you hit API limits:

1. **Check Quotas**: Go to [Google Cloud Console Quotas](https://console.cloud.google.com/apis/credentials)
2. **Request Increases**: Request quota increases if needed
3. **Reduce Frequency**: Consider reducing sync frequency

## Security Notes

- The app runs under `smcghee@gmail.com` but accesses `sloswimtiming@gmail.com`'s calendars
- Only the specific calendars that are shared will be accessible
- The app can only make changes to events, not delete calendars
- All access is logged in Google Cloud Console

## Advantages of This Approach

1. **Simple Setup**: No domain-wide delegation required
2. **Standard OAuth2**: Uses well-established OAuth2 flow
3. **Granular Control**: Only specific calendars are shared
4. **Audit Trail**: Clear logging of all access
5. **Easy Testing**: Can test locally with OAuth2

## Monitoring

Set up monitoring to track:

- **Sync Success Rate**: Should be 100%
- **Events Processed**: Tracks total events found
- **Changes Made**: Tracks actual modifications
- **Error Rates**: Should be 0%

The system will send daily email reports to `sloswimtiming@gmail.com` with detailed statistics.

## Best Practices

1. **Regular Testing**: Test the sync regularly
2. **Monitor Logs**: Check Cloud Run logs for errors
3. **Backup Data**: Keep backups of important calendar data
4. **Update Credentials**: Rotate OAuth2 credentials periodically
5. **Monitor Quotas**: Watch for API quota limits

This approach works well for regular Gmail accounts and provides a secure, auditable solution for cross-account calendar access. 