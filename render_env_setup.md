# Render Environment Variables Setup

This guide covers setting up environment variables for deploying the Google Calendar Sync application on Render.

## Required Environment Variables

Set these in your Render dashboard under your web service's "Environment" tab:

### 1. Core Application Variables (Required)
```
SPREADSHEET_ID=your_spreadsheet_id
GEMINI_API_KEY=your_gemini_api_key
FLASK_SECRET_KEY=your_generated_secret_key
```

### 2. Google OAuth Credentials (Required for Web Interface)
```
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_PROJECT_ID=your_google_cloud_project_id
```

### 3. Optional: Email Notifications
```
SEND_EMAIL=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
TO_EMAIL=recipient@example.com
```

### 4. Optional: Sync Configuration
```
USE_GEMINI=true
LOG_LEVEL=INFO
TIMEZONE=America/Los_Angeles
```

## How to Get These Values

### Google OAuth Credentials

1. **Go to Google Cloud Console**:
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable Required APIs**:
   - Go to "APIs & Services" > "Library"
   - Enable these APIs:
     - Google Sheets API
     - Google Calendar API

3. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Set application type to "Web application"
   - Add authorized redirect URIs:
     - `https://your-app-name.onrender.com/auth/callback`
     - `http://localhost:5000/auth/callback` (for local testing)
   - Copy the Client ID and Client Secret

4. **Get Project ID**:
   - Your project ID is shown in the top navigation bar
   - Or go to "IAM & Admin" > "Settings"

### Flask Secret Key

Generate a random secret key using one of these methods:

**Option 1: Using OpenSSL**
```bash
openssl rand -hex 32
```

**Option 2: Using Python**
```python
import secrets
print(secrets.token_hex(32))
```

**Option 3: Using Online Generator**
- Visit a secure random string generator
- Generate a 64-character hexadecimal string

### Gemini API Key (Optional)

1. **Go to Google AI Studio**:
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account

2. **Create API Key**:
   - Click "Create API Key"
   - Copy the generated key
   - Add it to your environment variables

## Setting Environment Variables in Render

### Step-by-Step Process

1. **Go to Render Dashboard**:
   - Visit [Render Dashboard](https://dashboard.render.com/)
   - Sign in with your GitHub account

2. **Create New Web Service**:
   - Click "New" > "Web Service"
   - Connect your GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `gunicorn app:app`

3. **Configure Environment Variables**:
   - Go to your web service dashboard
   - Click "Environment" tab
   - Add each variable with its value:
     ```
     GOOGLE_CLIENT_ID=your_google_oauth_client_id
     GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
     GOOGLE_PROJECT_ID=your_google_cloud_project_id
     FLASK_SECRET_KEY=your_generated_secret_key
     GEMINI_API_KEY=your_gemini_api_key  # Optional
     SPREADSHEET_ID=your_default_spreadsheet_id  # Optional
     ```

4. **Save and Deploy**:
   - Click "Save Changes"
   - Render will automatically redeploy your service

## Environment Variable Details

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SPREADSHEET_ID` | Google Spreadsheet ID | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms` |
| `GEMINI_API_KEY` | Gemini AI API key for AI parsing | `AIzaSyC...` |
| `FLASK_SECRET_KEY` | Flask session secret key | `a1b2c3d4e5f6...` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID (web interface) | `123456789-abcdef.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret (web interface) | `GOCSPX-abcdefghijklmnop` |
| `GOOGLE_PROJECT_ID` | Google Cloud project ID | `my-calendar-sync-project` |

### Optional Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SEND_EMAIL` | Enable email notifications | `true` |
| `USE_GEMINI` | Use Gemini parser | `true` |
| `SMTP_*` | Email server configuration | See email_config.md |

## Testing Your Setup

After setting the environment variables:

1. **Check Authentication**:
   - Your app should load without redirecting to `/setup`
   - Users can authenticate through Google OAuth

2. **Test Calendar Sync**:
   - Try syncing a small spreadsheet first
   - Check that events are created correctly
   - Verify calendar permissions

3. **Monitor Logs**:
   - Check Render logs for any errors
   - Verify API calls are successful

## Troubleshooting

### Common Issues

**Authentication Errors**:
- Verify OAuth credentials are correct
- Check that redirect URIs match your Render domain
- Ensure Google APIs are enabled

**Missing Environment Variables**:
- Double-check all required variables are set
- Verify variable names match exactly (case-sensitive)
- Restart your Render service after adding variables

**API Rate Limits**:
- Monitor Google API usage
- Implement rate limiting if needed
- Consider upgrading Google Cloud quotas

### Security Best Practices

1. **Never commit secrets to Git**:
   - Use environment variables for all secrets
   - Add `.env` files to `.gitignore`

2. **Rotate keys regularly**:
   - Update OAuth credentials periodically
   - Regenerate Flask secret key if compromised

3. **Monitor usage**:
   - Check Google Cloud Console for API usage
   - Monitor Render logs for errors

## Alternative Deployment Options

### Google Cloud Platform
For automated deployment with Cloud Scheduler:
```bash
./deploy.sh [PROJECT_ID]
```

### Local Development
For local testing:
```bash
python app.py
```

## Support

If you encounter issues:
1. Check the application logs in Render
2. Verify all environment variables are set correctly
3. Test with a simple spreadsheet first
4. Review the main README.md for detailed setup instructions 