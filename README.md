# SLOHS Sports Calendar Sync

A comprehensive Google Calendar synchronization system that syncs sports events from Google Spreadsheets to Google Calendars, featuring both a web-based admin interface and command-line tools.

## Features

- **Web-based Admin Interface**: Interactive web application for easy calendar management
- **Dual Parser System**: Choose between traditional parsing or Gemini AI-powered parsing
- **Multiple Calendar Support**: Creates both a main combined calendar and individual sport-specific calendars
- **Smart Sport Name Handling**: Uses sport name from spreadsheet or falls back to sheet name
- **Flexible Event Handling**: Supports both single-day and multi-day events
- **Advanced Time Parsing**: Handles various time formats and special cases
- **Public Calendar Support**: Makes all calendars public by default
- **Comprehensive Logging**: Detailed logging and error handling
- **Bulk Operations**: Process all sheets at once with the "APPLY ALL" feature

## Quick Start

### 1. Set up Virtual Environment

**Option A: Automated Setup (Recommended)**
```bash
./setup_venv.sh
```

**Option B: Manual Setup**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

**Option A: Interactive Setup (Recommended)**
```bash
python setup_env.py
```

**Option B: Manual Setup**
Create a `.env` file with your settings:
```bash
SPREADSHEET_ID=your-spreadsheet-id
GEMINI_API_KEY=your-gemini-api-key
FLASK_SECRET_KEY=your-secret-key
```

### Option 1: Web Interface (Recommended)

1. **Start the web application**:
   ```bash
   # Make sure virtual environment is activated
   source venv/bin/activate
   
   python app.py
   ```
   
   **Note**: If port 5000 is in use (common on macOS due to AirPlay), the app will automatically try alternative ports or you can specify a different port:
   ```bash
   python app.py --port 5001
   ```

2. **Access the interface**: Open your browser to `http://localhost:5000` (or the port shown in the console)

3. **Authenticate**: Click "Authenticate with Google" to grant access to your Google account

4. **Configure and sync**:
   - Enter your spreadsheet ID
   - Select the sheet to process
   - Choose your preferred parser (Gemini AI or traditional)
   - Preview events before applying
   - Apply changes to your calendars

### Option 2: Command Line

For automated or batch processing:

```bash
# Make sure virtual environment is activated
source venv/bin/activate

python calendar_sync.py
```

## Web Interface Features

### Interactive Event Preview
- View and verify events before syncing
- See exactly what will be created, updated, or deleted
- Real-time validation of event data

### Parser Selection
- **Gemini AI Parser**: Advanced AI-powered parsing for complex spreadsheet formats
- **Traditional Parser**: Reliable parsing for standard formats
- Automatic fallback if one parser fails

### Bulk Operations
- **ALL Button**: Loads and previews all sheets combined
- **APPLY ALL Button**: Creates calendar entries for all sheets simultaneously
- Detailed summary of processing results

### Authentication & Security
- Secure Google OAuth2 authentication
- Session management with automatic token refresh
- Environment variable support for production deployment

## Setup

### 1. Clone and Install

```bash
git clone <repository-url>
cd google_calendar_sync

# Set up virtual environment
./setup_venv.sh

# Or manually:
# python3 -m venv venv
# source venv/bin/activate  # On Windows: venv\Scripts\activate
# pip install -r requirements.txt
```

### 2. Google Cloud Project Setup

1. Create a new project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the following APIs:
   - Google Sheets API
   - Google Calendar API
   - Cloud Run API (for GCP deployment)
   - Cloud Build API (for GCP deployment)
   - Cloud Scheduler API (for GCP deployment)

### 3. OAuth Credentials Setup

#### Option A: Environment Variables (Recommended for Production)
Set these environment variables:
```bash
export GOOGLE_CLIENT_ID=your_google_oauth_client_id
export GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
export GOOGLE_PROJECT_ID=your_google_cloud_project_id
export FLASK_SECRET_KEY=your_generated_secret_key
export GEMINI_API_KEY=your_gemini_api_key  # Optional, for AI parsing
```

#### Option B: Credentials File (Development)
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to APIs & Services > Credentials
3. Create OAuth 2.0 Client ID credentials
4. Download the credentials and save as `credentials.json` in the project directory

### 4. Optional: Gemini AI Setup
For AI-powered parsing:
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Set the `GEMINI_API_KEY` environment variable

## Spreadsheet Format

The Google Spreadsheet should follow this structure:

### Traditional Parser Format
- **First row**: Sport name (or sheet name will be used as fallback)
- **Second row**: Headers
- **Subsequent rows**: Event data with columns:
  - Date (MM/DD or MM/DD/YYYY)
  - Opponent
  - Location
  - Time
  - Transportation (optional)
  - Release Time (optional)
  - Departure Time (optional)

### Gemini AI Parser Format
- **First row**: Sport name
- **Second row**: Column headers
- **Subsequent rows**: Event data with columns:
  - Start Datetime (required)
  - Event (required)
  - Location (required)
  - End Datetime (optional)
  - Recurrence (optional)

## Deployment Options

### Option 1: Render (Recommended for Web Interface)

1. **Push to GitHub**:
   ```bash
   ./deploy.sh
   ```

2. **Deploy on Render**:
   - Go to [Render](https://render.com)
   - Sign up/Login with GitHub
   - Click 'New Web Service'
   - Connect your GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `gunicorn app:app`
   - Add environment variables (see `render_env_setup.md`)

### Option 2: Google Cloud Run (Recommended for Automation)

For automated deployment with Cloud Scheduler and advanced monitoring:

```bash
# Deploy to Cloud Run
./deploy_cloud_run.sh YOUR_PROJECT_ID
```

This will:
- Enable required Google Cloud APIs
- Build and deploy the container to Cloud Run
- Set up hourly Cloud Scheduler job
- Create service accounts for security
- Configure monitoring and logging

**Benefits of Cloud Run:**
- Built-in scheduling with Cloud Scheduler
- Advanced monitoring and logging
- Automatic scaling
- Better cost optimization
- Native Google Cloud integration

See `CLOUD_RUN_DEPLOYMENT.md` for detailed instructions.

### Option 3: Google Cloud Platform (Legacy)

For automated deployment with Cloud Scheduler:

```bash
chmod +x deploy.sh
./deploy.sh [PROJECT_ID]
```

This will:
- Enable required Google Cloud APIs
- Store credentials securely in Secret Manager
- Build and deploy the container to Cloud Run
- Set up a daily Cloud Scheduler job

## Environment Variables

### Required Variables
- `SPREADSHEET_ID`: Your Google Spreadsheet ID
- `GEMINI_API_KEY`: Your Gemini API key (for AI parsing)
- `FLASK_SECRET_KEY`: A random secret key for Flask sessions

### Optional Variables
- `GOOGLE_CLIENT_ID`: Your Google OAuth client ID (for web interface)
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret (for web interface)
- `GOOGLE_PROJECT_ID`: For GCP deployment
- `SEND_EMAIL`: Enable email notifications (true/false)
- `USE_GEMINI`: Use Gemini parser (true/false)
- Email configuration (SMTP_* variables) for notifications

## Testing

Run the comprehensive test suite:

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# All tests
python -m pytest

# Specific test files
python -m unittest test_calendar_sync.py -v
python -m unittest test_gemini_parser.py -v
python -m unittest test_datetime_parser.py -v
```

## Error Handling

The system includes robust error handling for:
- Invalid dates and times
- Missing or malformed data
- API errors and rate limits
- Network connectivity issues
- Authentication token expiration
- Parser failures with automatic fallback

All errors are logged to `app.log` and `calendar_sync.log` for debugging.

## Troubleshooting

### Port 5000 Already in Use
If you see "Address already in use" on macOS:
1. **Option 1**: Disable AirPlay Receiver in System Preferences > General > AirDrop & Handoff
2. **Option 2**: Use a different port: `python app.py --port 5001`

### Authentication Issues
- Clear browser cookies and try again
- Check that your OAuth credentials are correctly configured
- Verify the redirect URIs include both localhost and your production domain

### Parser Issues
- Try switching between Gemini AI and traditional parser
- Check the debug logs for specific error messages
- Verify your spreadsheet format matches the expected structure

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 