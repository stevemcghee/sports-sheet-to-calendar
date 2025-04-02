# SLOHS Sports Calendar Sync

This script syncs sports events from a Google Spreadsheet to Google Calendars, creating both a main combined calendar and individual sport-specific calendars.

## Features

- Syncs sports events from Google Sheets to Google Calendar
- Creates a main combined calendar for all sports
- Creates individual sport-specific calendars
- Smart sport name handling (uses sport name from spreadsheet or falls back to sheet name)
- Handles both single-day and multi-day events
- Supports various time formats and special cases
- Makes all calendars public by default
- Provides detailed logging and error handling

## Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd google_calendar_sync
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up Google Cloud Project:
   - Create a new project in [Google Cloud Console](https://console.cloud.google.com)
   - Enable the following APIs:
     - Google Sheets API
     - Google Calendar API
     - Cloud Run API
     - Cloud Build API
     - Cloud Scheduler API

5. Set up Google OAuth 2.0 credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Navigate to APIs & Services > Credentials
   - Create OAuth 2.0 Client ID credentials
   - Download the credentials and save as `credentials.json` in the project directory

6. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update the following variables in `.env`:
     ```
     SPREADSHEET_ID=your_spreadsheet_id
     CALENDAR_NAME=SLOHS Sports
     PROJECT_ID=your_project_id
     REGION=us-central1
     TIMEZONE=America/Los_Angeles
     ```

## First Run

1. Run the script:
```bash
python calendar_sync.py
```

2. The first time you run the script, it will:
   - Open a browser window for Google OAuth authentication
   - Create the main sports calendar if it doesn't exist
   - Create individual sport calendars if they don't exist
   - Delete all existing events from the calendars
   - Process each sheet in the spreadsheet
   - Create events in both the main and sport-specific calendars

3. The script will display a summary of:
   - Total number of sports processed
   - Total number of events created
   - Number of events per sport

## Spreadsheet Format

The Google Spreadsheet should have the following structure:
- Each sheet represents a different sport
- First row: Sport name (or sheet name will be used as fallback)
- Second row: Headers
- Subsequent rows: Event data with columns:
  - Date (MM/DD or MM/DD/YYYY)
  - Opponent
  - Location
  - Time
  - Transportation (optional)
  - Release Time (optional)
  - Departure Time (optional)

## Testing

The script includes comprehensive tests for:
- Event parsing
- Date and time handling
- Calendar management
- Error cases and edge conditions

Run the tests with:
```bash
python -m unittest test_calendar_sync.py -v
```

## Error Handling

The script includes robust error handling for:
- Invalid dates and times
- Missing or malformed data
- API errors
- Empty sport names (falls back to sheet name)
- Network issues

All errors are logged to `out.log` for debugging.

## Deployment

The application can be deployed to Google Cloud Platform to run automatically:

1. Install the Google Cloud SDK and authenticate:
```bash
gcloud auth login
```

2. Make the deployment script executable:
```bash
chmod +x deploy.sh
```

3. Run the deployment script:
```bash
./deploy.sh [PROJECT_ID]
```

The deployment script will:
- Enable required Google Cloud APIs
- Store credentials securely in Secret Manager
- Build and deploy the container to Cloud Run
- Set up a daily Cloud Scheduler job

The calendar sync will run automatically every day at midnight in the configured timezone.

### Deployment Files

- `Dockerfile`: Defines the container image for the application
- `cloudbuild.yaml`: Configures the Cloud Build process
- `deploy.sh`: Automation script for deployment
- `.env`: Configuration file (not committed to version control)

### Environment Variables

The following environment variables are required for deployment:
- `SPREADSHEET_ID`: Google Sheets ID containing sports events
- `CALENDAR_NAME`: Name for the main sports calendar
- `PROJECT_ID`: Google Cloud project ID
- `REGION`: Google Cloud region (default: us-central1)
- `TIMEZONE`: Timezone for calendar events (default: America/Los_Angeles)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 