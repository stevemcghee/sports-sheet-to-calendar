from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from calendar_sync import (
    get_google_credentials, get_spreadsheet_data, parse_sports_events,
    create_or_get_sports_calendar, update_calendar, get_existing_events,
    events_are_equal, list_available_sheets, get_event_key
)
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
import os
from datetime import datetime
import json
import logging
import traceback
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
from dotenv import load_dotenv
import google.generativeai as genai
from google.auth.transport.requests import Request
import pytz
from gemini_parser import parse_sheet_with_gemini
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Set up logging to both file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to console
        logging.FileHandler('app.log')      # Log to file
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev')

# OAuth configuration
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/calendar'
]

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Initialize Google Calendar service
def get_calendar_service():
    try:
        logger.info("Attempting to get Google credentials...")
        creds = get_google_credentials()
        if not creds:
            logger.error("No credentials returned from get_google_credentials()")
            raise Exception("Failed to get Google credentials")
        
        if not creds.valid:
            logger.warning("Credentials are not valid, attempting to refresh...")
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Credentials refreshed successfully")
                except RefreshError as e:
                    logger.error(f"Failed to refresh credentials: {str(e)}")
                    # Delete the invalid token file
                    if os.path.exists('token.pickle'):
                        os.remove('token.pickle')
                        logger.info("Removed invalid token file")
                    raise Exception("Your Google Calendar access token has expired. Please refresh the page to re-authenticate.")
            else:
                logger.error("Credentials are invalid and cannot be refreshed")
                raise Exception("Invalid credentials. Please refresh the page to re-authenticate.")
        
        logger.info("Building calendar service...")
        service = build('calendar', 'v3', credentials=creds)
        logger.info("Calendar service built successfully")
        return service
    except Exception as e:
        logger.error(f"Error in get_calendar_service: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def get_sheets_service():
    """Get an authenticated Google Sheets service."""
    try:
        if 'credentials' not in session:
            raise Exception('Not authenticated with Google')
            
        # Get credentials from session
        credentials = Credentials(**session['credentials'])
        
        # Refresh token if needed
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            # Update session with new token
            session['credentials'] = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
        
        # Build and return the service
        return build('sheets', 'v4', credentials=credentials)
    except Exception as e:
        logger.error(f"Error getting sheets service: {str(e)}")
        raise

@app.route('/')
def index():
    try:
        logger.info("Rendering index page...")
        # Get spreadsheet ID from .env file
        spreadsheet_id = os.getenv('SPREADSHEET_ID')
        if not spreadsheet_id:
            logger.warning("No SPREADSHEET_ID found in .env file")
        return render_template('index.html', spreadsheet_id=spreadsheet_id)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('error.html', error_message=str(e)), 500

@app.route('/auth')
def auth():
    try:
        # Get the redirect URI from the request
        redirect_uri = request.url_root.rstrip('/') + '/auth/callback'
        logger.debug(f"Using redirect URI: {redirect_uri}")
        
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            SCOPES,
            redirect_uri=redirect_uri
        )
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent screen to ensure refresh token
        )
        return jsonify({'success': True, 'auth_url': auth_url})
    except Exception as e:
        logger.error(f"Error generating auth URL: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@app.route('/auth/callback')
def auth_callback():
    try:
        code = request.args.get('code')
        if not code:
            return """
            <html>
                <body>
                    <script>
                        window.opener.postMessage('auth_error', '*');
                        window.close();
                    </script>
                </body>
            </html>
            """
            
        # Get the redirect URI from the request
        redirect_uri = request.url_root.rstrip('/') + '/auth/callback'
        logger.debug(f"Using redirect URI: {redirect_uri}")
            
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            SCOPES,
            redirect_uri=redirect_uri
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Save credentials to session
        session['credentials'] = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        
        # Also save to token.pickle for command-line use
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            
        return """
        <html>
            <body>
                <script>
                    window.opener.postMessage('auth_complete', '*');
                    window.close();
                </script>
            </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error in auth callback: {str(e)}")
        logger.error(traceback.format_exc())
        return """
        <html>
            <body>
                <script>
                    window.opener.postMessage('auth_error', '*');
                    window.close();
                </script>
            </body>
        </html>
        """

@app.route('/check_auth')
def check_auth():
    try:
        # Check both Google OAuth and Gemini API key
        has_google_auth = bool(session.get('credentials'))
        has_gemini_key = bool(GEMINI_API_KEY)
        
        return jsonify({
            'authenticated': has_google_auth,
            'has_gemini_key': has_gemini_key,
            'error': None if has_google_auth and has_gemini_key else 'Missing authentication'
        })
    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'authenticated': False, 'error': str(e)})

@app.route('/load_sheet', methods=['POST'])
def load_sheet():
    try:
        # Check if user is authenticated
        if 'credentials' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401

        data = request.get_json()
        spreadsheet_id = data.get('spreadsheet_id')
        sheet_name = data.get('sheet_name')
        use_traditional_parser = data.get('use_traditional_parser', False)

        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'Spreadsheet ID is required'}), 400

        # Get the spreadsheet title
        sheets_service = get_sheets_service()
        try:
            spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            spreadsheet_title = spreadsheet.get('properties', {}).get('title', 'Untitled Spreadsheet')
            
            # Get available sheets if no sheet name is provided
            if not sheet_name:
                sheets = [sheet.get('properties', {}).get('title') for sheet in spreadsheet.get('sheets', [])]
                if sheets:
                    sheet_name = sheets[0]  # Default to first sheet
                else:
                    return jsonify({'success': False, 'error': 'No sheets found in spreadsheet'}), 400
            else:
                # Verify the requested sheet exists
                sheets = [sheet.get('properties', {}).get('title') for sheet in spreadsheet.get('sheets', [])]
                if sheet_name not in sheets:
                    return jsonify({
                        'success': False, 
                        'error': f'Sheet "{sheet_name}" not found',
                        'available_sheets': sheets
                    }), 400
        except HttpError as e:
            if e.resp.status == 404:
                return jsonify({'success': False, 'error': 'Spreadsheet not found'}), 404
            return jsonify({'success': False, 'error': f'Error accessing spreadsheet: {str(e)}'}), 500

        # Get the sheet data
        range_name = f'{sheet_name}!A:Z'  # Get all columns
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])

        if not values:
            return jsonify({
                'success': True,
                'spreadsheet_title': spreadsheet_title,
                'events': [],
                'message': 'No data found in sheet'
            })

        # Parse the events
        try:
            if use_traditional_parser:
                events = parse_sports_events(values, sheet_name)
            else:
                events = parse_sheet_with_gemini(values)
                
            if not events:
                return jsonify({
                    'success': True,
                    'spreadsheet_title': spreadsheet_title,
                    'events': [],
                    'message': 'No events found in sheet',
                    'parser_used': 'traditional' if use_traditional_parser else 'gemini'
                })
                
            return jsonify({
                'success': True,
                'spreadsheet_title': spreadsheet_title,
                'events': events,
                'parser_used': 'traditional' if use_traditional_parser else 'gemini'
            })
        except Exception as e:
            error_message = str(e)
            if not use_traditional_parser:
                error_message = f"Gemini parser error: {error_message}. Try using the traditional parser instead."
            return jsonify({
                'success': False,
                'error': error_message,
                'parser_used': 'traditional' if use_traditional_parser else 'gemini'
            }), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/preview_changes', methods=['POST'])
def preview_changes():
    try:
        data = request.get_json()
        spreadsheet_id = data.get('spreadsheet_id')
        sheet_name = data.get('sheet_name')
        use_traditional_parser = data.get('use_traditional_parser', False)  # Default to Gemini

        if not spreadsheet_id or not sheet_name:
            return jsonify({'success': False, 'error': 'Spreadsheet ID and sheet name are required'})

        # Get credentials
        credentials = Credentials(**session['credentials'])
        sheets_service = build('sheets', 'v4', credentials=credentials)
        calendar_service = build('calendar', 'v3', credentials=credentials)

        # Get sheet data
        values = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
        if not values:
            return jsonify({'success': False, 'error': 'No data found in sheet'})

        # Parse events using either Gemini or traditional parser
        if use_traditional_parser:
            logger.info("Using traditional parser")
            events = parse_sports_events(values, sheet_name)
        else:
            logger.info("Using Gemini parser")
            try:
                events = parse_sheet_with_gemini(values)
                if not events:
                    logger.warning("Gemini parser returned no events, falling back to traditional parser")
                    events = parse_sports_events(values, sheet_name)
            except Exception as e:
                logger.error(f"Error using Gemini parser: {str(e)}")
                logger.error(traceback.format_exc())
                logger.info("Falling back to traditional parser")
                events = parse_sports_events(values, sheet_name)

        # Get existing events
        calendar_id = create_or_get_sports_calendar(calendar_service, sheet_name)
        existing_events = get_existing_events(calendar_service, calendar_id)

        # Compare events
        changes = {
            'to_add': [],
            'to_update': [],
            'to_delete': []
        }

        # Find events to add or update
        for event in events:
            found = False
            for existing in existing_events:
                if events_are_equal(event, existing):
                    found = True
                    if not events_are_equal(event, existing, compare_all=True):
                        changes['to_update'].append({
                            'old': existing,
                            'new': event
                        })
                    break
            if not found:
                changes['to_add'].append(event)

        # Find events to delete
        for existing in existing_events:
            found = False
            for event in events:
                if events_are_equal(event, existing):
                    found = True
                    break
            if not found:
                changes['to_delete'].append(existing)

        return jsonify({
            'success': True,
            'changes': changes,
            'parser_used': 'traditional' if use_traditional_parser else 'gemini'
        })

    except Exception as e:
        logger.error(f"Error in preview_changes: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@app.route('/apply_changes', methods=['POST'])
def apply_changes():
    try:
        logger.info("Starting apply_changes route")
        service = get_calendar_service()
        calendar_name = f"{session['sheet_name']} Calendar"
        logger.info(f"Using calendar name: {calendar_name}")
        
        calendar_id = create_or_get_sports_calendar(service, calendar_name)
        logger.info(f"Got calendar ID: {calendar_id}")
        
        # Get proposed events from session
        proposed_events = session.get('proposed_events', [])
        logger.info(f"Found {len(proposed_events)} proposed events")
        
        if not proposed_events:
            logger.error("No events to apply")
            return jsonify({
                'success': False,
                'error': 'No events to apply'
            }), 400
        
        # Ensure we're working with dictionaries
        if not all(isinstance(event, dict) for event in proposed_events):
            logger.error("Invalid event format in proposed events")
            for i, event in enumerate(proposed_events):
                logger.error(f"Event {i}: {type(event)} - {event}")
            return jsonify({
                'success': False,
                'error': 'Invalid event format'
            }), 400
        
        # Validate each event
        for i, event in enumerate(proposed_events):
            try:
                logger.debug(f"\nValidating event {i+1}/{len(proposed_events)}")
                logger.debug(f"Event data: {event}")
                
                # Check required fields
                required_fields = ['summary', 'start', 'end']
                missing_fields = [field for field in required_fields if field not in event]
                if missing_fields:
                    logger.error(f"Event missing required fields: {missing_fields}")
                    logger.error(f"Event data: {event}")
                    continue
                
                # Check start/end structure
                if not isinstance(event['start'], dict) or not isinstance(event['end'], dict):
                    logger.error(f"Invalid start/end format in event: {event}")
                    logger.error(f"Start type: {type(event['start'])}")
                    logger.error(f"End type: {type(event['end'])}")
                    continue
                
                # Check dateTime fields
                if 'dateTime' not in event['start'] or 'dateTime' not in event['end']:
                    logger.error(f"Event missing dateTime in start/end: {event}")
                    logger.error(f"Start: {event['start']}")
                    logger.error(f"End: {event['end']}")
                    continue
                
                # Validate dateTime format
                try:
                    start_date = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                    end_date = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
                    logger.debug(f"Valid dates: {start_date} to {end_date}")
                except Exception as e:
                    logger.error(f"Error parsing dates: {str(e)}")
                    logger.error(f"Start time: {event['start']['dateTime']}")
                    logger.error(f"End time: {event['end']['dateTime']}")
                    continue
                
            except Exception as e:
                logger.error(f"Error validating event {i+1}: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Event data: {event}")
                logger.error(traceback.format_exc())
                continue
        
        # Apply changes
        logger.info("Applying changes to calendar")
        update_calendar(service, proposed_events, calendar_id)
        
        # Get updated calendar events for preview
        logger.debug("Fetching updated events")
        updated_events = get_existing_events(service, calendar_id)
        
        # Convert to list if it's a dictionary
        if isinstance(updated_events, dict):
            logger.debug("Converting updated events from dict to list")
            updated_events = list(updated_events.values())
        
        # Format events for response
        logger.debug("Formatting events for response")
        formatted_events = []
        for i, event in enumerate(updated_events):
            try:
                logger.debug(f"\nFormatting event {i+1}/{len(updated_events)}")
                logger.debug(f"Event data: {event}")
                
                if not isinstance(event, dict):
                    logger.error(f"Invalid event format: {event}")
                    continue
                
                start_date = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                formatted_date = start_date.strftime('%a, %b %d, %Y %I:%M %p')
                
                formatted_events.append({
                    'summary': event['summary'],
                    'location': event.get('location', 'N/A'),
                    'transportation': event.get('transportation', 'N/A'),
                    'release_time': event.get('release_time', 'N/A'),
                    'departure_time': event.get('departure_time', 'N/A'),
                    'formatted_date': formatted_date
                })
                
            except Exception as e:
                logger.error(f"Error formatting event {i+1}: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Event data: {event}")
                logger.error(traceback.format_exc())
                continue
        
        logger.info(f"Successfully applied changes. Updated {len(formatted_events)} events")
        return jsonify({
            'success': True,
            'events': formatted_events
        })
    except Exception as e:
        logger.error(f"Error in apply_changes: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

if __name__ == '__main__':
    app.run(debug=True) 