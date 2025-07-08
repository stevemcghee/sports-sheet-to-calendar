# Render Environment Variables Setup

## Required Environment Variables

Set these in your Render dashboard under your web service's "Environment" tab:

### 1. Google OAuth Credentials
```
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_PROJECT_ID=your_google_cloud_project_id
```

### 2. Flask Secret Key
```
FLASK_SECRET_KEY=your_generated_secret_key
```

### 3. Optional: Default Spreadsheet ID
```
SPREADSHEET_ID=your_default_spreadsheet_id
```

### 4. Optional: Gemini API Key
```
GEMINI_API_KEY=your_gemini_api_key
```

## How to Get These Values

### Google OAuth Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Sheets API and Google Calendar API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set application type to "Web application"
6. Add authorized redirect URIs:
   - `https://your-app-name.onrender.com/auth/callback`
   - `http://localhost:5000/auth/callback` (for local testing)
7. Copy the Client ID and Client Secret

### Flask Secret Key
Generate a random secret key:
```bash
openssl rand -hex 32
```

### Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key

## Setting Environment Variables in Render

1. Go to your Render dashboard
2. Click on your web service
3. Go to "Environment" tab
4. Add each variable with its value
5. Click "Save Changes"
6. Redeploy your service

## Testing

After setting the environment variables:
1. Your app should load without redirecting to `/setup`
2. Users can authenticate through Google OAuth
3. The app will work with your Google Sheets and Calendar 