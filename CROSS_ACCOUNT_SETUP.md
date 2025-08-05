# Cross-Account Calendar Access Setup

This guide helps you set up the calendar sync app to run under `smcghee@gmail.com` while accessing calendars owned by `sloswimtiming@gmail.com`.

## Overview

- **Deployment Account**: `smcghee@gmail.com` (runs the app)
- **Calendar Owner**: `sloswimtiming@gmail.com` (owns the calendars)
- **Schedule**: Nightly at 3 AM

## Step 1: sloswimtiming@gmail.com Setup

### 1.1 Enable Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/library)
2. Search for "Google Calendar API"
3. Click "Enable"

### 1.2 Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Application type: "Web application"
4. Add authorized redirect URIs:
   - `http://localhost:5000/auth/callback` (for local testing)
   - `https://your-cloud-run-url/auth/callback` (after deployment)
5. Add `smcghee@gmail.com` as a test user

### 1.3 Share Calendars

For each calendar that needs to be synced:

1. Go to [Google Calendar](https://calendar.google.com)
2. Right-click on the calendar name
3. Select "Settings and sharing"
4. Scroll to "Share with specific people"
5. Click "Add people"
6. Add `smcghee@gmail.com`
7. Set permission to "Make changes to events"
8. Click "Send"

### 1.4 Get Calendar IDs

1. In Google Calendar, right-click on each calendar
2. Select "Settings and sharing"
3. Scroll down to "Integrate calendar"
4. Copy the "Calendar ID" (looks like: `sloswimtiming@gmail.com` or `abc123@group.calendar.google.com`)

## Step 2: smcghee@gmail.com Setup

### 2.1 Deploy the Application

Run the deployment script:

```bash
chmod +x setup_cross_account_deployment.sh
./setup_cross_account_deployment.sh
```

### 2.2 Set Environment Variables

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Find your `calendar-sync` service
3. Click "Edit & Deploy New Revision"
4. Add these environment variables:

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

### 2.3 Test the Deployment

1. Visit your Cloud Run URL
2. Click "Authenticate with Google"
3. Sign in as `smcghee@gmail.com`
4. Grant permissions to access `sloswimtiming@gmail.com`'s calendars

## Step 3: Verify Setup

### 3.1 Test Manual Sync

1. Go to your Cloud Run URL
2. Click "Load Sheet" to test spreadsheet access
3. Click "Apply Changes" to test calendar access

### 3.2 Test Automated Sync

1. Go to [Cloud Scheduler Console](https://console.cloud.google.com/cloudscheduler)
2. Find your `calendar-sync-job`
3. Click "Run now" to test the scheduler
4. Check the logs for success

### 3.3 Monitor the System

- **Cloud Run Logs**: https://console.cloud.google.com/run
- **Scheduler Logs**: `gcloud scheduler jobs logs calendar-sync-job`
- **Email Notifications**: Check `sloswimtiming@gmail.com` for daily reports

## Troubleshooting

### Permission Denied Errors

If you get permission errors:

1. Verify `sloswimtiming@gmail.com` has shared the calendars
2. Check that `smcghee@gmail.com` is added as a test user in OAuth
3. Ensure the Google Calendar API is enabled

### Authentication Issues

If authentication fails:

1. Clear browser cookies for Google
2. Try authenticating again
3. Check that the OAuth redirect URIs are correct

### API Quota Issues

If you hit API limits:

1. Check [Google Cloud Console Quotas](https://console.cloud.google.com/apis/credentials)
2. Request quota increases if needed
3. Consider reducing sync frequency

## Security Notes

- The app runs under `smcghee@gmail.com` but accesses `sloswimtiming@gmail.com`'s calendars
- Only the specific calendars that are shared will be accessible
- The app can only make changes to events, not delete calendars
- All access is logged in Google Cloud Console

## Monitoring

Set up monitoring to track:

- **Sync Success Rate**: Should be 100%
- **Events Processed**: Tracks total events found
- **Changes Made**: Tracks actual modifications
- **Error Rates**: Should be 0%

The system will send daily email reports to `sloswimtiming@gmail.com` with detailed statistics. 