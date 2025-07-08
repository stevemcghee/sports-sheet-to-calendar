# Gemini Calendar Sync

A standalone web application that uses Google's Gemini AI to parse spreadsheet data and sync it to Google Calendar.

## Features

- Google OAuth authentication
- Spreadsheet data parsing using Gemini AI
- Multiple sheet support
- Event preview before syncing
- Custom calendar creation
- Timezone support (America/Los_Angeles)

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following variables:
   ```
   FLASK_SECRET_KEY=your_secret_key
   GEMINI_API_KEY=your_gemini_api_key
   ```

4. Set up Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the following APIs:
     - Google Sheets API
     - Google Calendar API
   - Create OAuth 2.0 credentials:
     - Application type: Web application
     - Authorized redirect URIs: `http://localhost:5000/auth/callback`
   - Download the credentials and save as `credentials.json` in the project root

5. Get a Gemini API key:
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create an API key
   - Add it to your `.env` file

## Usage

1. Start the application:
   ```bash
   python app.py
   ```

2. Open your browser and go to `http://localhost:5000`

3. Follow these steps:
   - Click "Authenticate with Google" to grant access to your Google account
   - Enter the spreadsheet ID you want to sync
   - Select the sheet to process
   - Preview the events
   - Enter a calendar name
   - Click "Apply to Calendar" to sync the events

## Spreadsheet Format

Your spreadsheet should follow this format:
- First row: Sport name
- Second row: Column headers
- Subsequent rows: Event data

Required columns:
- Start Datetime (required)
- Event (required)
- Location (required)
- End Datetime (optional)

## Notes

- The application uses the America/Los_Angeles timezone
- If End Datetime is missing, events will be set to 2 hours duration
- Invalid events will be skipped but processing will continue
- A new calendar will be created for each sync operation 