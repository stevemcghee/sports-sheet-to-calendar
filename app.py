from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from calendar_sync import (
    get_spreadsheet_data, parse_sports_events,
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
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email'
]

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)

# Configure safety settings
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]

model = genai.GenerativeModel('models/gemini-1.5-pro-latest', safety_settings=safety_settings)

# Initialize Google Calendar service
def get_calendar_service():
    try:
        logger.info("Attempting to get Google credentials...")
        
        # Check if user is authenticated via session
        if 'credentials' not in session:
            raise Exception('Not authenticated with Google')
            
        # Get credentials from session
        credentials = Credentials(**session['credentials'])
        
        # Refresh token if needed
        if credentials.expired and credentials.refresh_token:
            try:
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
                logger.info("Credentials refreshed successfully")
            except RefreshError as e:
                logger.error(f"Failed to refresh credentials: {str(e)}")
                # Clear invalid credentials from session
                session.pop('credentials', None)
                raise Exception("Your Google Calendar access token has expired. Please refresh the page to re-authenticate.")
        
        logger.info("Building calendar service...")
        service = build('calendar', 'v3', credentials=credentials)
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
            try:
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
            except RefreshError as e:
                logger.error(f"Failed to refresh credentials: {str(e)}")
                # Clear invalid credentials from session
                session.pop('credentials', None)
                raise Exception("Your Google access token has expired. Please re-authenticate.")
        
        # Build and return the service
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        logger.error(f"Error getting sheets service: {str(e)}")
        if 'invalid_grant' in str(e) or 'expired' in str(e) or 'revoked' in str(e):
            # Clear invalid credentials from session
            session.pop('credentials', None)
            raise Exception("Your Google access token has expired or been revoked. Please re-authenticate.")
        raise

@app.route('/')
def index():
    try:
        logger.info("Rendering index page...")
        
        # Check if we're in production (using environment variables)
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if client_id and client_secret:
            # Production mode - using environment variables
            logger.info("Using environment variables for OAuth credentials")
            # Create credentials.json from environment variables if it doesn't exist
            if not os.path.exists('credentials.json'):
                credentials_data = {
                    "installed": {
                        "client_id": client_id,
                        "project_id": os.getenv('GOOGLE_PROJECT_ID', 'default-project'),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_secret": client_secret,
                        "redirect_uris": [request.url_root.rstrip('/') + '/auth/callback']
                    }
                }
                
                # Save credentials to file
                with open('credentials.json', 'w') as f:
                    json.dump(credentials_data, f, indent=4)
                logger.info("Created credentials.json from environment variables")
        else:
            # Development mode - check for credentials.json file
            if not os.path.exists('credentials.json'):
                logger.warning("No credentials.json found and no environment variables set")
                return redirect(url_for('setup_credentials'))
            
        # Get spreadsheet ID from environment or .env file
        spreadsheet_id = os.getenv('SPREADSHEET_ID')
        if not spreadsheet_id:
            logger.warning("No SPREADSHEET_ID found in environment variables")
            
        return render_template('index.html', spreadsheet_id=spreadsheet_id)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('error.html', error_message=str(e)), 500

@app.route('/setup', methods=['GET', 'POST'])
def setup_credentials():
    # Check if we're already configured via environment variables
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    if client_id and client_secret:
        logger.info("OAuth credentials already configured via environment variables")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            credentials_data = {
                "installed": {
                    "client_id": request.form.get('client_id'),
                    "project_id": request.form.get('project_id'),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": request.form.get('client_secret'),
                    "redirect_uris": ["http://localhost"]
                }
            }
            
            # Save credentials to file
            with open('credentials.json', 'w') as f:
                json.dump(credentials_data, f, indent=4)
                
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Error saving credentials: {str(e)}")
            return render_template('setup.html', error=str(e))
    
    return render_template('setup.html')

@app.route('/auth')
def auth():
    try:
        # Clear any existing credentials to force fresh authentication
        session.pop('credentials', None)
        
        # Get the redirect URI from the request, force HTTPS
        base_url = request.url_root.rstrip('/')
        if base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://')
        redirect_uri = base_url + '/auth/callback'
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
            
        # Get the redirect URI from the request, force HTTPS
        base_url = request.url_root.rstrip('/')
        if base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://')
        redirect_uri = base_url + '/auth/callback'
        logger.debug(f"Using redirect URI: {redirect_uri}")
            
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            SCOPES,
            redirect_uri=redirect_uri
        )
        
        # Monkey patch to handle scope changes
        import oauthlib.oauth2.rfc6749.parameters
        original_validate = oauthlib.oauth2.rfc6749.parameters.validate_token_parameters
        
        def patched_validate(params):
            try:
                return original_validate(params)
            except Exception as e:
                if "Scope has changed" in str(e):
                    logger.info("Scope change detected - ignoring validation error")
                    return None
                raise e
        
        oauthlib.oauth2.rfc6749.parameters.validate_token_parameters = patched_validate
        
        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
        except Exception as e:
            # Restore original function
            oauthlib.oauth2.rfc6749.parameters.validate_token_parameters = original_validate
            raise e
        
        # Restore original function
        oauthlib.oauth2.rfc6749.parameters.validate_token_parameters = original_validate
        
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
        
        user_email = None
        if has_google_auth:
            try:
                # Get user info from Google API
                credentials = Credentials(**session['credentials'])
                logger.info(f"Credentials scopes: {credentials.scopes}")
                service = build('oauth2', 'v2', credentials=credentials)
                user_info = service.userinfo().get().execute()
                user_email = user_info.get('email')
                logger.info(f"Successfully retrieved user email: {user_email}")
                logger.info(f"Full user info: {user_info}")
            except Exception as e:
                logger.warning(f"Could not get user email: {str(e)}")
                logger.warning(f"Error type: {type(e)}")
                logger.warning(f"Error details: {traceback.format_exc()}")
                user_email = "Unknown User (re-authenticate to see email)"
        
        return jsonify({
            'authenticated': has_google_auth,
            'has_gemini_key': has_gemini_key,
            'user_email': user_email,
            'error': None if has_google_auth and has_gemini_key else 'Missing authentication'
        })
    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'authenticated': False, 'error': str(e)})

@app.route('/logout')
def logout():
    try:
        # Clear credentials from session
        session.pop('credentials', None)
        
        # Also clear the token.pickle file if it exists
        try:
            if os.path.exists('token.pickle'):
                os.remove('token.pickle')
                logger.info("Removed token.pickle file")
        except Exception as e:
            logger.warning(f"Could not remove token.pickle: {str(e)}")
        
        logger.info("User logged out successfully")
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@app.route('/load_sheet', methods=['POST'])
def load_sheet():
    try:
        # Check if user is authenticated
        if 'credentials' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated', 'needs_auth': True}), 401

        data = request.get_json()
        spreadsheet_id = data.get('spreadsheet_id')
        sheet_name = data.get('sheet_name')
        use_traditional_parser = data.get('use_traditional_parser', False)

        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'Spreadsheet ID is required'}), 400

        # Create a custom log handler to capture debug logs
        class CaptureLogHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.logs = []
                
            def emit(self, record):
                log_entry = self.format(record)
                self.logs.append(log_entry)
        
        # Set up the capture handler
        capture_handler = CaptureLogHandler()
        capture_handler.setLevel(logging.DEBUG)
        capture_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # Add the handler to the calendar_sync logger
        from calendar_sync import logger as calendar_logger
        calendar_logger.addHandler(capture_handler)

        try:
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
                    'message': 'No data found in sheet',
                    'debug_logs': capture_handler.logs
                })

            # Parse the events
            try:
                if use_traditional_parser:
                    events = parse_sports_events(values, sheet_name)
                else:
                    # Use Gemini parser
                    logger.info("Starting Gemini parser analysis...")
                    logger.info(f"Processing {len(values)} rows with Gemini")
                    events = parse_sheet_with_gemini(values)
                    logger.info(f"Gemini parser completed, found {len(events)} events")
                    if not events:
                        # If Gemini parser returns no events, try traditional parser as fallback
                        logger.warning("Gemini parser returned no events, trying traditional parser")
                        events = parse_sports_events(values, sheet_name)
                    
                if not events:
                    return jsonify({
                        'success': True,
                        'spreadsheet_title': spreadsheet_title,
                        'events': [],
                        'message': 'No events found in sheet',
                        'parser_used': 'traditional' if use_traditional_parser else 'gemini',
                        'sheets': sheets,
                        'debug_logs': capture_handler.logs
                    })
                    
                return jsonify({
                    'success': True,
                    'spreadsheet_title': spreadsheet_title,
                    'events': events,
                    'parser_used': 'traditional' if use_traditional_parser else 'gemini',
                    'sheets': sheets,
                    'debug_logs': capture_handler.logs
                })
            except Exception as e:
                logger.error(f"Error parsing events: {str(e)}")
                logger.error(traceback.format_exc())
                return jsonify({
                    'success': False, 
                    'error': f'Error parsing events: {str(e)}',
                    'debug_logs': capture_handler.logs
                }), 500

        except Exception as e:
            error_msg = str(e)
            if 'invalid_grant' in error_msg or 'expired' in error_msg or 'revoked' in error_msg:
                # Clear invalid credentials from session
                session.pop('credentials', None)
                return jsonify({
                    'success': False, 
                    'error': 'Your session has expired. Please re-authenticate.',
                    'needs_auth': True,
                    'debug_logs': capture_handler.logs
                }), 401
            raise
        finally:
            # Remove the capture handler
            calendar_logger.removeHandler(capture_handler)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in load_sheet route: {error_msg}")
        logger.error(traceback.format_exc())
        if 'invalid_grant' in error_msg or 'expired' in error_msg or 'revoked' in error_msg:
            # Clear invalid credentials from session
            session.pop('credentials', None)
            return jsonify({
                'success': False, 
                'error': 'Your session has expired. Please re-authenticate.',
                'needs_auth': True
            }), 401
        return jsonify({'success': False, 'error': error_msg}), 500

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
            logger.info(f"Processing {len(values)} rows with Gemini")
            try:
                events = parse_sheet_with_gemini(values)
                logger.info(f"Gemini parser completed, found {len(events)} events")
                if not events:
                    logger.warning("Gemini parser returned no events, falling back to traditional parser")
                    events = parse_sports_events(values, sheet_name)
            except Exception as e:
                logger.error(f"Error using Gemini parser: {str(e)}")
                logger.error(traceback.format_exc())
                logger.info("Falling back to traditional parser")
                events = parse_sports_events(values, sheet_name)

        # Get existing events
        # Handle special case for "All Sports"
        if sheet_name == 'All Sports':
            calendar_name = 'SLOHS All Sports'
        else:
            calendar_name = f"SLOHS {sheet_name}"
        calendar_id = create_or_get_sports_calendar(calendar_service, calendar_name)
        existing_events = get_existing_events(calendar_service, calendar_id)

        # Convert existing events to list if it's a dictionary
        if isinstance(existing_events, dict):
            existing_events = list(existing_events.values())

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
                    # Note: events_are_equal already does a full comparison
                    # so we don't need a separate compare_all parameter
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
    print("DEBUG: apply_changes route called")  # This will show in console
    # Set up log capture
    class CaptureLogHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.logs = []
        
        def emit(self, record):
            log_entry = self.format(record)
            self.logs.append(log_entry)
    
    capture_handler = CaptureLogHandler()
    capture_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    capture_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(capture_handler)
    logger.info("Log capture handler set up successfully for apply_changes route")
    
    try:
        data = request.get_json()
        spreadsheet_id = data.get('spreadsheet_id')
        sheet_name = data.get('sheet_name')
        use_traditional_parser = data.get('use_traditional_parser', False)

        if not spreadsheet_id or not sheet_name:
            return jsonify({'success': False, 'error': 'Spreadsheet ID and sheet name are required'})

        logger.info("Starting apply_changes route")
        logger.info("TEST LOG: This should appear in debug logs")
        logger.info(f"Received data: {data}")
        logger.info(f"Spreadsheet ID: {spreadsheet_id}")
        logger.info(f"Sheet name: {sheet_name}")
        logger.info(f"Use traditional parser: {use_traditional_parser}")
        service = get_calendar_service()
        
        # Handle special case for "All Sports"
        if sheet_name == 'All Sports':
            calendar_name = 'SLOHS All Sports'
        else:
            calendar_name = f"SLOHS {sheet_name}"
        logger.info(f"Using calendar name: {calendar_name}")
        
        calendar_id = create_or_get_sports_calendar(service, calendar_name)
        logger.info(f"Got calendar ID: {calendar_id}")
        
        # Get credentials for sheets service
        credentials = Credentials(**session['credentials'])
        sheets_service = build('sheets', 'v4', credentials=credentials)
        
        # Get sheet data and parse events
        values = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
        if not values:
            return jsonify({'success': False, 'error': 'No data found in sheet'})

        # Parse events using either Gemini or traditional parser
        if use_traditional_parser:
            logger.info("Using traditional parser")
            events = parse_sports_events(values, sheet_name)
        else:
            logger.info("Using Gemini parser")
            logger.info(f"Processing {len(values)} rows with Gemini")
            try:
                events = parse_sheet_with_gemini(values)
                logger.info(f"Gemini parser completed, found {len(events)} events")
                if not events:
                    logger.warning("Gemini parser returned no events, falling back to traditional parser")
                    events = parse_sports_events(values, sheet_name)
            except Exception as e:
                logger.error(f"Error using Gemini parser: {str(e)}")
                logger.error(traceback.format_exc())
                logger.info("Falling back to traditional parser")
                events = parse_sports_events(values, sheet_name)
        
        logger.info(f"Found {len(events)} events to apply")
        
        if not events:
            logger.error("No events to apply")
            return jsonify({
                'success': False,
                'error': 'No events to apply'
            }), 400
        
        # Ensure we're working with dictionaries
        if not all(isinstance(event, dict) for event in events):
            logger.error("Invalid event format in events")
            for i, event in enumerate(events):
                logger.error(f"Event {i}: {type(event)} - {event}")
            return jsonify({
                'success': False,
                'error': 'Invalid event format'
            }), 400
        
        # Validate each event
        for i, event in enumerate(events):
            try:
                logger.debug(f"\nValidating event {i+1}/{len(events)}")
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
                
                # Check for dateTime or date fields (handle both timed and all-day events)
                if 'dateTime' not in event['start'] and 'date' not in event['start']:
                    logger.error(f"Event missing dateTime or date in start: {event}")
                    logger.error(f"Start: {event['start']}")
                    continue
                
                if 'dateTime' not in event['end'] and 'date' not in event['end']:
                    logger.error(f"Event missing dateTime or date in end: {event}")
                    logger.error(f"End: {event['end']}")
                    continue
                
                # Validate date format
                try:
                    if 'dateTime' in event['start']:
                        start_date = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                        end_date = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
                        logger.debug(f"Valid timed event: {start_date} to {end_date}")
                    else:
                        # All-day event
                        start_date = datetime.fromisoformat(event['start']['date'])
                        end_date = datetime.fromisoformat(event['end']['date'])
                        logger.debug(f"Valid all-day event: {start_date} to {end_date}")
                except Exception as e:
                    logger.error(f"Error parsing dates: {str(e)}")
                    logger.error(f"Start: {event['start']}")
                    logger.error(f"End: {event['end']}")
                    continue
                
            except Exception as e:
                logger.error(f"Error validating event {i+1}: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Event data: {event}")
                logger.error(traceback.format_exc())
                continue
        
        # Apply changes
        logger.info("Applying changes to calendar")
        update_calendar(service, events, calendar_id)
        
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
                
                # Handle both timed and all-day events
                if 'dateTime' in event['start']:
                    start_date = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                    formatted_date = start_date.strftime('%a, %b %d, %Y %I:%M %p')
                elif 'date' in event['start']:
                    start_date = datetime.fromisoformat(event['start']['date'])
                    formatted_date = start_date.strftime('%a, %b %d, %Y') + ' (All Day)'
                else:
                    logger.error(f"Event has neither dateTime nor date: {event}")
                    continue
                
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
        logger.info(f"TEST LOG: Captured {len(capture_handler.logs)} log entries")
        return jsonify({
            'success': True,
            'events': formatted_events,
            'debug_logs': capture_handler.logs
        })
    except Exception as e:
        logger.error(f"Error in apply_changes: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'debug_logs': capture_handler.logs
        }), 400
    finally:
        # Remove the handler to avoid duplicate logs
        root_logger.removeHandler(capture_handler)

@app.route('/apply_all_sheets', methods=['POST'])
def apply_all_sheets():
    """Apply changes to all sheets at once."""
    # Set up log capture
    class CaptureLogHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.logs = []
        
        def emit(self, record):
            log_entry = self.format(record)
            self.logs.append(log_entry)
    
    capture_handler = CaptureLogHandler()
    capture_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    capture_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(capture_handler)
    
    try:
        data = request.get_json()
        spreadsheet_id = data.get('spreadsheet_id')
        use_traditional_parser = data.get('use_traditional_parser', False)

        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'Spreadsheet ID is required'})

        logger.info("Starting apply_all_sheets route")
        service = get_calendar_service()
        
        # Get credentials for sheets service
        credentials = Credentials(**session['credentials'])
        sheets_service = build('sheets', 'v4', credentials=credentials)
        
        # Get all available sheets
        logger.info("Getting all available sheets")
        available_sheets = list_available_sheets(sheets_service, spreadsheet_id)
        
        if not available_sheets:
            return jsonify({'success': False, 'error': 'No sheets found in spreadsheet'})
        
        logger.info(f"Found {len(available_sheets)} sheets: {available_sheets}")
        
        # Track results for each sheet
        sheet_results = {}
        total_events_created = 0
        total_events_updated = 0
        total_events_deleted = 0
        
        # Process each sheet
        for sheet_name in available_sheets:
            logger.info(f"Processing sheet: {sheet_name}")
            
            try:
                # Get sheet data
                values = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
                if not values:
                    logger.warning(f"No data found in sheet: {sheet_name}")
                    sheet_results[sheet_name] = {
                        'success': False,
                        'error': 'No data found in sheet',
                        'events_created': 0,
                        'events_updated': 0,
                        'events_deleted': 0
                    }
                    continue
                
                # Parse events
                if use_traditional_parser:
                    logger.info(f"Using traditional parser for {sheet_name}")
                    events = parse_sports_events(values, sheet_name)
                else:
                    logger.info(f"Using Gemini parser for {sheet_name}")
                    try:
                        events = parse_sheet_with_gemini(values)
                        if not events:
                            logger.warning(f"Gemini parser returned no events for {sheet_name}, falling back to traditional parser")
                            events = parse_sports_events(values, sheet_name)
                    except Exception as e:
                        logger.error(f"Error using Gemini parser for {sheet_name}: {str(e)}")
                        logger.info(f"Falling back to traditional parser for {sheet_name}")
                        events = parse_sports_events(values, sheet_name)
                
                if not events:
                    logger.warning(f"No events found in sheet: {sheet_name}")
                    sheet_results[sheet_name] = {
                        'success': True,
                        'events_created': 0,
                        'events_updated': 0,
                        'events_deleted': 0,
                        'message': 'No events found in sheet'
                    }
                    continue
                
                # Create or get calendar for this sheet
                calendar_name = f"SLOHS {sheet_name}"
                calendar_id = create_or_get_sports_calendar(service, calendar_name)
                
                # Update calendar with events
                logger.info(f"Updating calendar for {sheet_name} with {len(events)} events")
                deleted, inserted, changed = update_calendar(service, events, calendar_id)
                
                # Track results
                sheet_results[sheet_name] = {
                    'success': True,
                    'events_created': inserted,
                    'events_updated': changed,
                    'events_deleted': deleted,
                    'total_events': len(events)
                }
                
                total_events_created += inserted
                total_events_updated += changed
                total_events_deleted += deleted
                
                logger.info(f"Successfully processed {sheet_name}: {inserted} created, {changed} updated, {deleted} deleted")
                
            except Exception as e:
                logger.error(f"❌ Error processing sheet {sheet_name}: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Provide more detailed error information
                error_details = str(e)
                if "timeRangeEmpty" in error_details:
                    error_details = "Invalid event times detected. Some events have end times before start times."
                elif "HttpError" in error_details:
                    error_details = f"Google Calendar API error: {error_details}"
                
                sheet_results[sheet_name] = {
                    'success': False,
                    'error': error_details,
                    'events_created': 0,
                    'events_updated': 0,
                    'events_deleted': 0
                }
        
        # Prepare summary
        successful_sheets = [name for name, result in sheet_results.items() if result['success']]
        failed_sheets = [name for name, result in sheet_results.items() if not result['success']]
        
        logger.info(f"Bulk operation completed. Successful sheets: {len(successful_sheets)}, Failed sheets: {len(failed_sheets)}")
        logger.info(f"Total events created: {total_events_created}, updated: {total_events_updated}, deleted: {total_events_deleted}")
        
        return jsonify({
            'success': True,
            'summary': {
                'total_sheets': len(available_sheets),
                'successful_sheets': len(successful_sheets),
                'failed_sheets': len(failed_sheets),
                'total_events_created': total_events_created,
                'total_events_updated': total_events_updated,
                'total_events_deleted': total_events_deleted
            },
            'sheet_results': sheet_results,
            'debug_logs': capture_handler.logs
        })
        
    except Exception as e:
        logger.error(f"Error in apply_all_sheets: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'debug_logs': capture_handler.logs
        }), 400
    finally:
        # Remove the handler to avoid duplicate logs
        root_logger.removeHandler(capture_handler)

@app.route('/apply_all_to_master_calendar', methods=['POST'])
def apply_all_to_master_calendar():
    """Create or update a calendar called 'SLOHS All Sports' with all events from all sheets."""
    class CaptureLogHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.logs = []
        def emit(self, record):
            log_entry = self.format(record)
            self.logs.append(log_entry)
    capture_handler = CaptureLogHandler()
    capture_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    capture_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(capture_handler)
    try:
        data = request.get_json()
        spreadsheet_id = data.get('spreadsheet_id')
        use_traditional_parser = data.get('use_traditional_parser', False)
        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'Spreadsheet ID is required'})
        logger.info("Starting apply_all_to_master_calendar route")
        service = get_calendar_service()
        credentials = Credentials(**session['credentials'])
        sheets_service = build('sheets', 'v4', credentials=credentials)
        # Get all available sheets
        available_sheets = list_available_sheets(sheets_service, spreadsheet_id)
        if not available_sheets:
            return jsonify({'success': False, 'error': 'No sheets found in spreadsheet'})
        all_events = []
        for sheet_name in available_sheets:
            values = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
            if not values:
                continue
            if use_traditional_parser:
                events = parse_sports_events(values, sheet_name)
            else:
                try:
                    events = parse_sheet_with_gemini(values)
                    if not events:
                        events = parse_sports_events(values, sheet_name)
                except Exception as e:
                    logger.error(f"Error using Gemini parser for {sheet_name}: {str(e)}")
                    events = parse_sports_events(values, sheet_name)
            if events:
                all_events.extend(events)
        # Create or get the 'SLOHS All Sports' calendar
        calendar_name = 'SLOHS All Sports'
        calendar_id = create_or_get_sports_calendar(service, calendar_name)
        logger.info(f"Updating '{calendar_name}' calendar with {len(all_events)} events")
        deleted, inserted, changed = update_calendar(service, all_events, calendar_id)
        logger.info(f"{calendar_name} calendar: {inserted} created, {changed} updated, {deleted} deleted")
        return jsonify({
            'success': True,
            'calendar_name': calendar_name,
            'events_created': inserted,
            'events_updated': changed,
            'events_deleted': deleted,
            'total_events': len(all_events),
            'debug_logs': capture_handler.logs
        })
    except Exception as e:
        logger.error(f"Error in apply_all_to_master_calendar: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e), 'debug_logs': capture_handler.logs}), 400
    finally:
        root_logger.removeHandler(capture_handler)

@app.route('/preview_all_sheets', methods=['POST'])
def preview_all_sheets():
    """Preview all events from all sheets that would be added to the 'SLOHS All Sports' calendar."""
    class CaptureLogHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.logs = []
        def emit(self, record):
            log_entry = self.format(record)
            self.logs.append(log_entry)
    capture_handler = CaptureLogHandler()
    capture_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    capture_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(capture_handler)
    try:
        data = request.get_json()
        spreadsheet_id = data.get('spreadsheet_id')
        use_traditional_parser = data.get('use_traditional_parser', False)
        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'Spreadsheet ID is required'})
        logger.info("Starting preview_all_sheets route")
        credentials = Credentials(**session['credentials'])
        sheets_service = build('sheets', 'v4', credentials=credentials)
        # Get all available sheets
        available_sheets = list_available_sheets(sheets_service, spreadsheet_id)
        if not available_sheets:
            return jsonify({'success': False, 'error': 'No sheets found in spreadsheet'})
        all_events = []
        for sheet_name in available_sheets:
            values = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
            if not values:
                continue
            if use_traditional_parser:
                events = parse_sports_events(values, sheet_name)
            else:
                try:
                    events = parse_sheet_with_gemini(values)
                    if not events:
                        events = parse_sports_events(values, sheet_name)
                except Exception as e:
                    logger.error(f"Error using Gemini parser for {sheet_name}: {str(e)}")
                    events = parse_sports_events(values, sheet_name)
            if events:
                all_events.extend(events)
        logger.info(f"Preview: Found {len(all_events)} events from all sheets")
        return jsonify({
            'success': True,
            'events': all_events,
            'total_events': len(all_events),
            'debug_logs': capture_handler.logs
        })
    except Exception as e:
        logger.error(f"Error in preview_all_sheets: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e), 'debug_logs': capture_handler.logs}), 400
    finally:
        root_logger.removeHandler(capture_handler)

@app.route('/get_slohs_calendars', methods=['GET'])
def get_slohs_calendars():
    """Get all SLOHS calendars for the logged-in user."""
    try:
        service = get_calendar_service()
        
        # Get all calendars for the user
        calendar_list = service.calendarList().list().execute()
        slohs_calendars = []
        
        for calendar in calendar_list.get('items', []):
            calendar_name = calendar.get('summary', '')
            if calendar_name.startswith('SLOHS '):
                calendar_id = calendar['id']
                
                # Get the first event to determine the start month
                try:
                    events_result = service.events().list(
                        calendarId=calendar_id,
                        timeMin=datetime.now().isoformat() + 'Z',
                        maxResults=1,
                        orderBy='startTime',
                        singleEvents=True
                    ).execute()
                    
                    first_event_date = None
                    if events_result.get('items'):
                        event = events_result['items'][0]
                        if 'dateTime' in event['start']:
                            first_event_date = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                        elif 'date' in event['start']:
                            first_event_date = datetime.fromisoformat(event['start']['date'])
                    
                    slohs_calendars.append({
                        'id': calendar_id,
                        'name': calendar_name,
                        'first_event_date': first_event_date.isoformat() if first_event_date else None
                    })
                except Exception as e:
                    logger.error(f"Error getting events for calendar {calendar_name}: {str(e)}")
                    # Still include the calendar even if we can't get events
                    slohs_calendars.append({
                        'id': calendar_id,
                        'name': calendar_name,
                        'first_event_date': None
                    })
        
        return jsonify({
            'success': True,
            'calendars': slohs_calendars
        })
        
    except Exception as e:
        logger.error(f"Error in get_slohs_calendars: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_current_calendar', methods=['POST'])
def get_current_calendar():
    """Get current calendar events for preview."""
    try:
        data = request.get_json()
        sheet_name = data.get('sheet_name')
        
        if not sheet_name:
            return jsonify({'success': False, 'error': 'Sheet name is required'})

        service = get_calendar_service()
        
        # Handle special case for "All Sports"
        if sheet_name == 'All Sports':
            calendar_name = 'SLOHS All Sports'
        else:
            calendar_name = f"SLOHS {sheet_name}"
        
        # Try to get existing calendar
        try:
            calendar_id = create_or_get_sports_calendar(service, calendar_name)
        except Exception as e:
            # If calendar doesn't exist yet, return empty list
            return jsonify({
                'success': True,
                'events': [],
                'calendar_name': calendar_name,
                'message': 'Calendar does not exist yet'
            })
        
        # Get existing events
        existing_events = get_existing_events(service, calendar_id)
        
        # Convert to list if it's a dictionary
        if isinstance(existing_events, dict):
            existing_events = list(existing_events.values())
        
        # Format events for response
        formatted_events = []
        for event in existing_events:
            try:
                if not isinstance(event, dict):
                    continue
                
                # Handle both timed and all-day events
                if 'dateTime' in event['start']:
                    start_date = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                    formatted_date = start_date.strftime('%a, %b %d, %Y %I:%M %p')
                elif 'date' in event['start']:
                    start_date = datetime.fromisoformat(event['start']['date'])
                    formatted_date = start_date.strftime('%a, %b %d, %Y') + ' (All Day)'
                else:
                    continue
                
                formatted_events.append({
                    'summary': event['summary'],
                    'location': event.get('location', 'N/A'),
                    'transportation': event.get('transportation', 'N/A'),
                    'release_time': event.get('release_time', 'N/A'),
                    'departure_time': event.get('departure_time', 'N/A'),
                    'formatted_date': formatted_date
                })
                
            except Exception as e:
                logger.error(f"Error formatting event: {str(e)}")
                continue
        
        # Sort events by date
        formatted_events.sort(key=lambda x: datetime.strptime(x['formatted_date'].split(' (')[0], '%a, %b %d, %Y %I:%M %p') if ' (All Day)' not in x['formatted_date'] else datetime.strptime(x['formatted_date'].replace(' (All Day)', ''), '%a, %b %d, %Y'))
        
        return jsonify({
            'success': True,
            'events': formatted_events,
            'calendar_name': calendar_name,
            'total_events': len(formatted_events)
        })
        
    except Exception as e:
        logger.error(f"Error in get_current_calendar: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})



import subprocess

@app.route('/routes')
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        url = urllib.parse.unquote(url_for(rule.endpoint, **options))
        line = "{:50s} {:20s} {}".format(rule.endpoint, methods, url)
        output.append(line)

    return "<pre>" + "\n".join(sorted(output)) + "</pre>"

@app.route('/trigger-sync', methods=['GET', 'POST'])
def trigger_sync():
    try:
        if 'credentials' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated', 'needs_auth': True}), 401
        # Get the absolute path to the automated_sync.py script
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'automated_sync.py'))
        
        # Get the python executable path from the sys module
        python_executable = sys.executable

        # Start the sync script as a background process
        subprocess.Popen([python_executable, script_path])
        
        return jsonify({'success': True, 'message': 'Sync triggered successfully!'})
    except Exception as e:
        logger.error(f"Error triggering sync: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True) 