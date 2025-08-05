# Owner Account Setup Guide

This guide helps you set up the calendar sync app where `sloswimtiming@gmail.com` owns both the app and the calendars.

## Overview

- **Account**: `sloswimtiming@gmail.com` (owns both app and calendars)
- **Authentication**: OAuth2 for accessing own calendars
- **Schedule**: Nightly at 3 AM

## Step 1: Set Up Google Cloud Project

### 1.1 Create or Use Existing Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Sign in as `sloswimtiming@gmail.com`
3. Create a new project or use an existing one
4. Note the Project ID

### 1.2 Enable Required APIs

1. Go to [Google Cloud Console APIs](https://console.cloud.google.com/apis/library)
2. Enable these APIs:
   - Cloud Build API
   - Cloud Run API
   - Cloud Scheduler API
   - Google Calendar API
   - Google Sheets API

## Step 2: Set Up OAuth2 Credentials

### 2.1 Create OAuth2 Client ID

1. Go to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Application type: "Web application"
4. Add authorized redirect URIs:
   - `http://localhost:5000/auth/callback` (for local testing)
   - `https://your-cloud-run-url/auth/callback` (after deployment)
5. Add test user: `sloswimtiming@gmail.com`

### 2.2 Download Credentials

1. Click "Download JSON" to get your OAuth2 credentials
2. Save as `credentials.json` in your project directory

## Step 3: Deploy the Application

### 3.1 Authenticate with Google Cloud

```bash
gcloud auth login
# Sign in as sloswimtiming@gmail.com
```

### 3.2 Run Deployment Script

```bash
chmod +x deploy_owner_account.sh
./deploy_owner_account.sh
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
3. Sign in as `sloswimtiming@gmail.com`
4. Grant permissions to access your calendars

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

1. **Check OAuth2 Setup**: Ensure OAuth2 credentials are configured correctly
2. **Check Test Users**: Verify `sloswimtiming@gmail.com` is in test users list
3. **Check APIs**: Ensure all required APIs are enabled

### Authentication Issues

If authentication fails:

1. **Clear Browser Cookies**: Clear cookies for Google
2. **Check Redirect URIs**: Ensure Cloud Run URL is in authorized redirect URIs
3. **Check Test Users**: Verify email is in test users list

### API Quota Issues

If you hit API limits:

1. **Check Quotas**: Go to [Google Cloud Console Quotas](https://console.cloud.google.com/apis/credentials)
2. **Request Increases**: Request quota increases if needed
3. **Reduce Frequency**: Consider reducing sync frequency

## Security Notes

- The app runs as `sloswimtiming@gmail.com` and accesses its own calendars
- No cross-account permissions needed
- All access is logged in Google Cloud Console
- Standard OAuth2 flow provides security

## Advantages of This Approach

1. **Simplest Setup**: No cross-account complexity
2. **Direct Access**: App can access all own calendars
3. **Standard OAuth2**: Uses well-established OAuth2 flow
4. **No Sharing Required**: No need to share calendars
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

## Migration from Cross-Account

If you're migrating from a cross-account setup:

1. **Backup Current Data**: Export current calendar data
2. **Test New Setup**: Verify new setup works
3. **Update Environment**: Set new environment variables
4. **Deploy New Version**: Deploy with owner account
5. **Monitor**: Watch for any issues
6. **Cleanup**: Remove old cross-account permissions

This approach is the simplest and most secure for single-account calendar management. 