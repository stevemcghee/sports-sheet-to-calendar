# Gemini Calendar Sync (Standalone Version)

A standalone web application that uses Google's Gemini AI to parse spreadsheet data and sync it to Google Calendar. This is a simplified version of the main calendar sync system, focused specifically on AI-powered parsing.

## Features

- **AI-Powered Parsing**: Uses Google's Gemini AI to intelligently parse spreadsheet data
- **Google OAuth Authentication**: Secure authentication with Google services
- **Multiple Sheet Support**: Process individual sheets or all sheets at once
- **Event Preview**: Preview parsed events before syncing to calendar
- **Custom Calendar Creation**: Create new calendars or update existing ones
- **Timezone Support**: Configured for America/Los_Angeles timezone
- **Error Handling**: Robust error handling with detailed logging

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   export FLASK_SECRET_KEY=your_secret_key
   export GEMINI_API_KEY=your_gemini_api_key
   ```

3. **Configure Google OAuth**:
   - Create OAuth 2.0 credentials in Google Cloud Console
   - Set application type to "Web application"
   - Add redirect URI: `http://localhost:5000/auth/callback`
   - Save as `credentials.json` in the project root

4. **Start the application**:
   ```bash
   python app.py
   ```

5. **Access the interface**: Open `http://localhost:5000` in your browser

## Setup Details

### Google Cloud Project Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - Google Sheets API
   - Google Calendar API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:5000/auth/callback`
5. Download the credentials and save as `credentials.json`

### Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your environment variables:
   ```bash
   export GEMINI_API_KEY=your_gemini_api_key
   ```

## Usage

1. **Authenticate**: Click "Authenticate with Google" to grant access
2. **Enter Spreadsheet ID**: Provide the Google Sheets ID you want to sync
3. **Select Sheet**: Choose which sheet to process (or process all sheets)
4. **Preview Events**: Review the AI-parsed events before syncing
5. **Enter Calendar Name**: Specify the target calendar name
6. **Apply Changes**: Click "Apply to Calendar" to sync the events

## Spreadsheet Format

Your spreadsheet should follow this format:

### Required Structure
- **First row**: Sport name
- **Second row**: Column headers
- **Subsequent rows**: Event data

### Required Columns
- **Start Datetime** (required): Event start time
- **Event** (required): Event name/description
- **Location** (required): Event location

### Optional Columns
- **End Datetime**: Event end time (defaults to 2 hours after start)
- **Recurrence**: Recurring event pattern

### Supported Datetime Formats
- `YYYY-MM-DD HH:MM`
- `MM/DD/YYYY HH:MM`
- Relative dates (e.g., "next Monday")
- Recurring patterns (e.g., "every Monday")

## AI Parsing Features

### Intelligent Data Recognition
- Automatically identifies sport names from sheet headers
- Parses various datetime formats
- Handles missing or incomplete data gracefully
- Supports recurring event patterns

### Error Handling
- Skips invalid events but continues processing
- Provides detailed error messages
- Maintains data integrity during parsing

### Event Formatting
- **Summary format**: `{sport_name}: {event_name} @ {location}`
- **Description format**: `Location: {location}`
- **Timezone**: All events use America/Los_Angeles timezone
- **Duration**: Default 2-hour duration if end time not specified

## Notes

- The application uses the America/Los_Angeles timezone by default
- If End Datetime is missing, events will be set to 2 hours duration
- Invalid events will be skipped but processing will continue
- A new calendar will be created for each sync operation if it doesn't exist
- The AI parser can handle various spreadsheet formats and data inconsistencies

## Troubleshooting

### Authentication Issues
- Clear browser cookies and try again
- Verify OAuth credentials are correctly configured
- Check that redirect URIs match your setup

### Parsing Issues
- Verify spreadsheet format matches requirements
- Check that required columns are present
- Review error logs for specific parsing issues

### API Limits
- Be aware of Google API rate limits
- Large spreadsheets may take time to process
- Consider processing sheets individually for large datasets

## Differences from Main System

This standalone version focuses specifically on AI-powered parsing, while the main system (`../app.py`) includes:
- Traditional parsing as an alternative
- More comprehensive web interface
- Bulk operations across multiple sheets
- Advanced deployment options
- Command-line interface

## License

This project is licensed under the MIT License. 