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
app.secret_key = os.urandom(24)  # Required for session management

# OAuth configuration
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/calendar'
]

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
        
        # Save credentials
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

@app.route('/load_sheet', methods=['POST'])
def load_sheet():
    try:
        logger.info("Loading sheet data...")
        data = request.json
        spreadsheet_id = data.get('spreadsheet_id')
        sheet_name = data.get('sheet_name')
        
        if not spreadsheet_id:
            logger.error("Missing spreadsheet_id")
            return jsonify({
                'success': False,
                'error': 'Missing spreadsheet_id'
            }), 400
        
        logger.info(f"Getting Google credentials for spreadsheet: {spreadsheet_id}")
        creds = get_google_credentials()
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Get spreadsheet title
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        spreadsheet_title = spreadsheet.get('properties', {}).get('title', 'Untitled Spreadsheet')
        
        # If no sheet name provided, list available sheets
        if not sheet_name:
            logger.info("No sheet name provided, listing available sheets")
            sheets = list_available_sheets(sheets_service, spreadsheet_id)
            return jsonify({
                'success': True,
                'sheets': sheets,
                'spreadsheet_title': spreadsheet_title
            })
        
        logger.info("Getting spreadsheet data...")
        sheet_data = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
        events = parse_sports_events(sheet_data, sheet_name)
        
        session['proposed_events'] = events
        session['spreadsheet_id'] = spreadsheet_id
        session['sheet_name'] = sheet_name
        
        logger.info(f"Successfully loaded {len(events)} events")
        return jsonify({
            'success': True,
            'events': events,
            'spreadsheet_title': spreadsheet_title,
            'sheet_name': sheet_name
        })
    except Exception as e:
        logger.error(f"Error in load_sheet: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/preview_changes', methods=['POST'])
def preview_changes():
    try:
        logger.info("Starting preview_changes route")
        service = get_calendar_service()
        calendar_name = f"{session['sheet_name']} Calendar"
        logger.info(f"Using calendar name: {calendar_name}")
        
        calendar_id = create_or_get_sports_calendar(service, calendar_name)
        logger.info(f"Got calendar ID: {calendar_id}")
        
        # Get existing events
        logger.debug("Fetching existing events")
        existing_events = get_existing_events(service, calendar_id)
        logger.info(f"Found {len(existing_events)} existing events")
        
        # Get proposed events from session
        proposed_events = session.get('proposed_events', [])
        logger.info(f"Found {len(proposed_events)} proposed events")
        
        # Convert existing events to list if it's a dictionary
        if isinstance(existing_events, dict):
            logger.debug("Converting existing events from dict to list")
            existing_events = list(existing_events.values())
        
        # Compare events
        changes = []
        for i, event in enumerate(proposed_events):
            try:
                logger.debug(f"\nProcessing proposed event {i+1}/{len(proposed_events)}")
                logger.debug(f"Event data: {event}")
                
                # Validate event structure
                if not isinstance(event, dict):
                    logger.error(f"Invalid event format: {event}")
                    continue
                    
                if 'start' not in event or 'end' not in event:
                    logger.error(f"Event missing start/end times: {event}")
                    continue
                    
                if not isinstance(event['start'], dict) or not isinstance(event['end'], dict):
                    logger.error(f"Invalid start/end format in event: {event}")
                    continue
                    
                if 'dateTime' not in event['start'] or 'dateTime' not in event['end']:
                    logger.error(f"Event missing dateTime in start/end: {event}")
                    logger.error(f"Start: {event['start']}")
                    logger.error(f"End: {event['end']}")
                    continue
                
                # Format the date for display
                try:
                    start_date = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                    formatted_date = start_date.strftime('%a, %b %d, %Y %I:%M %p')
                    logger.debug(f"Formatted date: {formatted_date}")
                except Exception as e:
                    logger.error(f"Error formatting date: {str(e)}")
                    logger.error(f"Event start time: {event['start']['dateTime']}")
                    continue
                
                # Check if event exists
                existing_event = next(
                    (e for e in existing_events if events_are_equal(e, event)),
                    None
                )
                
                if existing_event:
                    logger.debug(f"Found existing event: {event['summary']}")
                    changes.append({
                        'type': 'update',
                        'event': event,
                        'date': event['start']['dateTime'],  # For sorting
                        'formatted_date': formatted_date,
                        'summary': event['summary'],
                        'location': event.get('location', 'N/A'),
                        'transportation': event.get('transportation', 'N/A'),
                        'release_time': event.get('release_time', 'N/A'),
                        'departure_time': event.get('departure_time', 'N/A')
                    })
                else:
                    logger.debug(f"New event: {event['summary']}")
                    changes.append({
                        'type': 'create',
                        'event': event,
                        'date': event['start']['dateTime'],  # For sorting
                        'formatted_date': formatted_date,
                        'summary': event['summary'],
                        'location': event.get('location', 'N/A'),
                        'transportation': event.get('transportation', 'N/A'),
                        'release_time': event.get('release_time', 'N/A'),
                        'departure_time': event.get('departure_time', 'N/A')
                    })
                    
            except Exception as e:
                logger.error(f"Error processing proposed event {i+1}: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Event data: {event}")
                logger.error(traceback.format_exc())
                continue
        
        # Find events to delete
        logger.debug("Checking for events to delete")
        for i, event in enumerate(existing_events):
            try:
                logger.debug(f"\nChecking existing event {i+1}/{len(existing_events)}")
                logger.debug(f"Event data: {event}")
                
                if not any(events_are_equal(event, e) for e in proposed_events):
                    logger.debug(f"Event to delete: {event['summary']}")
                    
                    # Format the date for display
                    try:
                        start_date = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                        formatted_date = start_date.strftime('%a, %b %d, %Y %I:%M %p')
                        logger.debug(f"Formatted date: {formatted_date}")
                    except Exception as e:
                        logger.error(f"Error formatting date: {str(e)}")
                        logger.error(f"Event start time: {event['start']['dateTime']}")
                        continue
                    
                    changes.append({
                        'type': 'delete',
                        'event': event,
                        'date': event['start']['dateTime'],  # For sorting
                        'formatted_date': formatted_date,
                        'summary': event['summary'],
                        'location': event.get('location', 'N/A'),
                        'transportation': event.get('transportation', 'N/A'),
                        'release_time': event.get('release_time', 'N/A'),
                        'departure_time': event.get('departure_time', 'N/A')
                    })
                    
            except Exception as e:
                logger.error(f"Error processing existing event {i+1}: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Event data: {event}")
                logger.error(traceback.format_exc())
                continue
        
        # Sort changes by date
        logger.debug("Sorting changes by date")
        changes.sort(key=lambda x: x['date'])
        
        # Remove the temporary date field before returning
        for change in changes:
            del change['date']
        
        logger.info(f"Preview completed. Found {len(changes)} changes")
        return jsonify({
            'success': True,
            'changes': changes
        })
    except Exception as e:
        logger.error(f"Error in preview_changes: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

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

@app.route('/check_auth')
def check_auth():
    try:
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
                if creds and creds.valid:
                    return jsonify({'authenticated': True})
        return jsonify({'authenticated': False})
    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'authenticated': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True) 