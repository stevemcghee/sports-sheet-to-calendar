# Service Account Setup with Domain-Wide Delegation

This guide helps you set up a service account that can access `sloswimtiming@gmail.com`'s calendars without requiring individual calendar sharing.

## Overview

- **Service Account**: Runs the calendar sync app
- **Target User**: `sloswimtiming@gmail.com` (calendar owner)
- **Authentication**: Domain-wide delegation allows service account to act as target user

## Step 1: Create Service Account (Automated)

The deployment script will create:
- Service account: `calendar-sync-sa@your-project.iam.gserviceaccount.com`
- Service account key: `service-account-key.json`
- Required IAM permissions

## Step 2: Enable Domain-Wide Delegation

### 2.1 In Google Cloud Console

1. Go to [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Find your service account: `calendar-sync-sa@your-project.iam.gserviceaccount.com`
3. Click the pencil icon to edit
4. Check "Enable Google Workspace Domain-wide Delegation"
5. Click "Save"

### 2.2 Get Client ID

1. In the same service account page, click "Keys" tab
2. Note the "Client ID" (you'll need this for the next step)

## Step 3: Configure Google Workspace Admin

### 3.1 Access Google Workspace Admin

1. Go to [Google Workspace Admin Console](https://admin.google.com)
2. Sign in as a Google Workspace admin
3. Navigate to: Security > API Controls > Domain-wide Delegation

### 3.2 Add Domain-Wide Delegation

1. Click "Add new"
2. Enter the Client ID from Step 2.2
3. Add these OAuth scopes:
   ```
   https://www.googleapis.com/auth/calendar
   https://www.googleapis.com/auth/spreadsheets.readonly
   ```
4. Click "Authorize"

## Step 4: Deploy the Application

Run the deployment script:

```bash
chmod +x deploy_with_service_account.sh
./deploy_with_service_account.sh
```

## Step 5: Set Environment Variables

In Cloud Run console, add these environment variables:

```
SPREADSHEET_ID=your-spreadsheet-id
GEMINI_API_KEY=your-gemini-api-key
FLASK_SECRET_KEY=your-secret-key
TARGET_USER_EMAIL=sloswimtiming@gmail.com
SEND_EMAIL=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sloswimtiming@gmail.com
SMTP_PASSWORD=your-app-password
TO_EMAIL=sloswimtiming@gmail.com
```

## Step 6: Test the Setup

### 6.1 Test Service Account Authentication

```bash
# Test the service account locally
python calendar_sync_service_account.py
```

### 6.2 Test Cloud Run Deployment

1. Visit your Cloud Run URL
2. The app should work without OAuth authentication
3. Test the sync functionality

## Troubleshooting

### Permission Denied Errors

If you get permission errors:

1. **Check Domain-Wide Delegation**: Ensure it's enabled in Google Cloud Console
2. **Verify Client ID**: Make sure the Client ID in Google Workspace Admin matches your service account
3. **Check OAuth Scopes**: Ensure all required scopes are added
4. **Verify Target User**: Check that `TARGET_USER_EMAIL` is set correctly

### Service Account Key Issues

If the service account key is missing:

1. **Recreate Key**: 
   ```bash
   gcloud iam service-accounts keys create service-account-key.json \
       --iam-account=calendar-sync-sa@your-project.iam.gserviceaccount.com
   ```

2. **Check Permissions**: Ensure the service account has the necessary roles

### Calendar Access Issues

If calendar access fails:

1. **Check Target User**: Verify `sloswimtiming@gmail.com` exists and is accessible
2. **Test with Different Calendar**: Try with a different calendar ID
3. **Check Logs**: Look at Cloud Run logs for detailed error messages

## Security Considerations

### Service Account Security

- **Key Rotation**: Regularly rotate the service account key
- **Minimal Permissions**: Only grant necessary permissions
- **Audit Logs**: Monitor service account usage

### Domain-Wide Delegation Security

- **Scope Limitation**: Only request necessary OAuth scopes
- **User Limitation**: Only delegate to necessary users
- **Monitoring**: Monitor delegation usage

## Monitoring

### Cloud Logging

Monitor these log entries:
- Service account authentication
- Calendar API calls
- Error messages

### Cloud Monitoring

Set up alerts for:
- Authentication failures
- API quota limits
- Service account usage

## Advantages of Service Account Approach

1. **No Individual Permissions**: Don't need to share each calendar individually
2. **Centralized Management**: All permissions managed in one place
3. **Audit Trail**: Clear logging of all access
4. **Scalability**: Easy to add more calendars/users
5. **Security**: More secure than individual OAuth tokens

## Migration from OAuth2

If you're migrating from OAuth2:

1. **Backup Current Data**: Export current calendar data
2. **Test Service Account**: Verify service account works
3. **Update Environment**: Set new environment variables
4. **Deploy New Version**: Deploy with service account
5. **Monitor**: Watch for any issues
6. **Cleanup**: Remove old OAuth tokens

## Best Practices

1. **Use Environment Variables**: Never hardcode credentials
2. **Rotate Keys Regularly**: Change service account keys periodically
3. **Monitor Usage**: Track API calls and errors
4. **Test Thoroughly**: Verify all functionality works
5. **Document Changes**: Keep track of configuration changes

The service account approach provides a more robust and secure solution for cross-account calendar access. 