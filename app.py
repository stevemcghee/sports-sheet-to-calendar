from flask import Flask, Response, render_template, request, jsonify, session, redirect, url_for
from calendar_sync import (
    get_spreadsheet_data, parse_sports_events,
    create_or_get_sports_calendar, update_calendar, get_existing_events,
    events_are_equal, list_available_sheets, get_event_key, calculate_changes
)
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
import os
import io
from datetime import datetime
import json
import logging
import traceback
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
import pickle
from dotenv import load_dotenv
from google.auth.transport.requests import Request
import pytz
from googleapiclient.errors import HttpError
from dateutil import parser
from google.cloud import secretmanager

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

# Global variable to store the resolved default spreadsheet ID
DEFAULT_SPREADSHEET_ID_FROM_SECRET = None
INITIAL_SPREADSHEET_ID_ENV_VAR = os.getenv('SPREADSHEET_ID')

def _access_secret_version_raw(secret_version_id):
    """Access the payload of the given secret version directly from Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(name=secret_version_id)
        return response.payload.data.decode('UTF-8')
    except Exception as e:
        logger.error(f"Failed to access secret version {secret_version_id}: {e}")
        raise

def access_secret_version(secret_version_id):
    """Access the payload of the given secret version if it's a secret path.
    This function is for general secrets (like client ID/secret) that are not cached globally."""
    if not isinstance(secret_version_id, str) or not secret_version_id.startswith('projects/'):
        return secret_version_id # Not a secret manager path, return as is
    return _access_secret_version_raw(secret_version_id)

def resolve_spreadsheet_id(input_id):
    """Resolves the spreadsheet ID, using the cached default if applicable."""
    global DEFAULT_SPREADSHEET_ID_FROM_SECRET
    global INITIAL_SPREADSHEET_ID_ENV_VAR

    # If the input ID is the original secret path from env var, use the cached resolved value
    if input_id == INITIAL_SPREADSHEET_ID_ENV_VAR and DEFAULT_SPREADSHEET_ID_FROM_SECRET is not None:
        logger.debug("Using cached default spreadsheet ID.")
        return DEFAULT_SPREADSHEET_ID_FROM_SECRET
    
    # Otherwise, resolve it (either it's a new secret path or a direct ID)
    resolved_id = access_secret_version(input_id)

    # If the resolved ID came from the initial env var, and not yet cached, cache it
    if input_id == INITIAL_SPREADSHEET_ID_ENV_VAR and DEFAULT_SPREADSHEET_ID_FROM_SECRET is None:
        DEFAULT_SPREADSHEET_ID_FROM_SECRET = resolved_id
        logger.info("Cached default spreadsheet ID from Secret Manager.")

    return resolved_id

# At app startup, resolve the default spreadsheet ID once if it's a secret path
if INITIAL_SPREADSHEET_ID_ENV_VAR and INITIAL_SPREADSHEET_ID_ENV_VAR.startswith('projects/'):
    try:
        DEFAULT_SPREADSHEET_ID_FROM_SECRET = _access_secret_version_raw(INITIAL_SPREADSHEET_ID_ENV_VAR)
        logger.info("Pre-resolved default SPREADSHEET_ID from Secret Manager at startup.")
    except Exception as e:
        logger.error(f"Failed to pre-resolve default SPREADSHEET_ID at startup: {e}")
        # Keep DEFAULT_SPREADSHEET_ID_FROM_SECRET as None, so it will be resolved on first request
        DEFAULT_SPREADSHEET_ID_FROM_SECRET = None

# OAuth configuration
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

def get_client_config():
    """Constructs the client configuration for OAuth, fetching secrets from Secret Manager if necessary."""
    client_id_val = os.getenv('GOOGLE_CLIENT_ID')
    client_secret_val = os.getenv('GOOGLE_CLIENT_SECRET')

    client_id = access_secret_version(client_id_val)
    client_secret = access_secret_version(client_secret_val)

    logger.info(f"Using Client ID: {client_id[:10]}...") # Log only a prefix for security
    
    if not client_id or not client_secret:
        raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set and accessible.")

    return {
        "web": {
            "client_id": client_id,
            "project_id": os.getenv('GOOGLE_PROJECT_ID', 'default-project'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": [request.url_root.rstrip('/') + '/auth/callback']
        }
    }

# Initialize Google Calendar service
def get_calendar_service():
    try:
        logger.info("Attempting to get Google credentials...")
        
        # Check if user is authenticated via session
        if 'credentials' not in session:
            logger.info("No credentials in session.")
            # If not in session, try to load from token.pickle
            if os.path.exists('token.pickle'):
                logger.info("Loading credentials from token.pickle")
                with open('token.pickle', 'rb') as token:
                    credentials = pickle.load(token)
                    # Save credentials to session
                    session['credentials'] = {
                        'token': credentials.token,
                        'refresh_token': credentials.refresh_token,
                        'token_uri': credentials.token_uri,
                        'client_id': credentials.client_id,
                        'client_secret': credentials.client_secret,
                        'scopes': credentials.scopes
                    }
                    logger.info("Credentials loaded from token.pickle and saved to session.")
            else:
                logger.warning("No token.pickle file found.")
                raise Exception('Not authenticated with Google')
        else:
            logger.info("Credentials found in session.")
            
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
        logger.info("Attempting to get Google sheets credentials...")
        if 'credentials' not in session:
            logger.info("No credentials in session for sheets.")
            # If not in session, try to load from token.pickle
            if os.path.exists('token.pickle'):
                logger.info("Loading credentials from token.pickle for sheets")
                with open('token.pickle', 'rb') as token:
                    credentials = pickle.load(token)
                    # Save credentials to session
                    session['credentials'] = {
                        'token': credentials.token,
                        'refresh_token': credentials.refresh_token,
                        'token_uri': credentials.token_uri,
                        'client_id': credentials.client_id,
                        'client_secret': credentials.client_secret,
                        'scopes': credentials.scopes
                    }
                    logger.info("Credentials loaded from token.pickle and saved to session for sheets.")
            else:
                logger.warning("No token.pickle file found for sheets.")
                raise Exception('Not authenticated with Google')
        else:
            logger.info("Credentials found in session for sheets.")
            
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
                logger.info("Credentials refreshed successfully for sheets.")
            except RefreshError as e:
                logger.error(f"Failed to refresh credentials for sheets: {str(e)}")
                # Clear invalid credentials from session
                session.pop('credentials', None)
                raise Exception("Your Google access token has expired. Please re-authenticate.")
        
        # Build and return the service
        service = build('sheets', 'v4', credentials=credentials)
        logger.info("Sheets service built successfully.")
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
        # Get spreadsheet ID from environment or .env file
        spreadsheet_id_val = os.getenv('SPREADSHEET_ID')
        
        # If not set by env var, try to load from config file
        if not spreadsheet_id_val:
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    spreadsheet_id_val = config.get('spreadsheet_id')
                logger.info(f"Loaded spreadsheet_id from config.json: {spreadsheet_id_val}")
            except (FileNotFoundError, json.JSONDecodeError):
                logger.info("config.json not found or is invalid. No spreadsheet_id loaded.")
                spreadsheet_id_val = None
        
        # Pass the resolved value to the template
        resolved_spreadsheet_id = resolve_spreadsheet_id(spreadsheet_id_val)
        return render_template('index.html', spreadsheet_id=resolved_spreadsheet_id)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('error.html', error_message=str(e)), 500

@app.route('/auth')
def auth():
    try:
        # Clear any existing credentials to force fresh authentication
        session.pop('credentials', None)

        # Get the redirect URI from the request, force HTTPS in production
        redirect_uri = url_for('auth_callback', _external=True)
        if 'http://' in redirect_uri and 'localhost' not in redirect_uri:
             redirect_uri = redirect_uri.replace('http://', 'https://')

        logger.debug(f"Using redirect URI: {redirect_uri}")

        flow = Flow.from_client_config(
            get_client_config(),
            scopes=SCOPES,
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

        # Get the redirect URI from the request, force HTTPS in production
        redirect_uri = url_for('auth_callback', _external=True)
        if 'http://' in redirect_uri and 'localhost' not in redirect_uri:
             redirect_uri = redirect_uri.replace('http://', 'https://')
        
        logger.debug(f"Using redirect URI in callback: {redirect_uri}")

        flow = Flow.from_client_config(
            get_client_config(),
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        logger.info(f"Fetching token with redirect URI: {redirect_uri}")
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
        logger.info("Credentials saved to session.")

        # Also save to token.pickle for command-line use
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            logger.info("Credentials saved to token.pickle.")

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
        logger.info("Checking authentication status...")
        
        if 'credentials' not in session:
            logger.info("No credentials in session. Checking for token.pickle.")
            if os.path.exists('token.pickle'):
                logger.info("Loading credentials from token.pickle")
                with open('token.pickle', 'rb') as token:
                    credentials = pickle.load(token)
                    # Save credentials to session
                    session['credentials'] = {
                        'token': credentials.token,
                        'refresh_token': credentials.refresh_token,
                        'token_uri': credentials.token_uri,
                        'client_id': credentials.client_id,
                        'client_secret': credentials.client_secret,
                        'scopes': credentials.scopes
                    }
                    logger.info("Credentials loaded from token.pickle and saved to session.")
            else:
                logger.info("No token.pickle file found.")

        has_google_auth = bool(session.get('credentials'))
        logger.info(f"Session credentials exist: {has_google_auth}")
        
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
        else:
            logger.info("No session credentials found.")
        
        return jsonify({
            'authenticated': has_google_auth,
            'user_email': user_email,
            'error': None if has_google_auth else 'Missing authentication'
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

@app.route('/load_initial_data', methods=['POST'])
def load_initial_data():
    """
    Loads initial data for the spreadsheet, including title, URL, and sheets,
    without loading the event data itself. This is for faster initial page load.
    """
    try:
        if 'credentials' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated', 'needs_auth': True}), 401

        data = request.get_json()
        spreadsheet_id_val = data.get('spreadsheet_id')
        spreadsheet_id = resolve_spreadsheet_id(spreadsheet_id_val)

        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'Spreadsheet ID is required'}), 400

        sheets_service = get_sheets_service()
        try:
            spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            spreadsheet_title = spreadsheet.get('properties', {}).get('title', 'Untitled Spreadsheet')
            spreadsheet_url = spreadsheet.get('spreadsheetUrl')
            sheets = [sheet.get('properties', {}).get('title') for sheet in spreadsheet.get('sheets', []) if not sheet.get('properties', {}).get('hidden', False)]
            
            return jsonify({
                'success': True,
                'spreadsheet_title': spreadsheet_title,
                'spreadsheet_url': spreadsheet_url,
                'sheets': sheets
            })
        except HttpError as e:
            if e.resp.status == 404:
                return jsonify({'success': False, 'error': 'Spreadsheet not found'}), 404
            return jsonify({'success': False, 'error': f'Error accessing spreadsheet: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Error in load_initial_data: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/load_sheet', methods=['POST'])
def load_sheet():
    try:
        # Check if user is authenticated
        if 'credentials' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated', 'needs_auth': True}), 401

        data = request.get_json()
        spreadsheet_id_val = data.get('spreadsheet_id')
        sheet_name = data.get('sheet_name')

        spreadsheet_id = resolve_spreadsheet_id(spreadsheet_id_val)

        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'Spreadsheet ID is required'}), 400

        # Save the original value (which could be the secret path) to the config file
        if spreadsheet_id_val:
            try:
                with open('config.json', 'w') as f:
                    json.dump({'spreadsheet_id': spreadsheet_id_val}, f)
                logger.info(f"Saved spreadsheet_id to config.json: {spreadsheet_id_val}")
            except Exception as e:
                logger.error(f"Error saving spreadsheet_id to config.json: {e}")

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
                spreadsheet_url = spreadsheet.get('spreadsheetUrl')
                
                # Get available sheets if no sheet name is provided
                if not sheet_name:
                    sheets = [sheet.get('properties', {}).get('title') for sheet in spreadsheet.get('sheets', []) if not sheet.get('properties', {}).get('hidden', False)]
                    if sheets:
                        sheet_name = sheets[0]  # Default to first visible sheet
                    else:
                        return jsonify({'success': False, 'error': 'No visible sheets found in spreadsheet'}), 400
                else:
                    # Verify the requested sheet exists and is not hidden
                    sheets = [sheet.get('properties', {}).get('title') for sheet in spreadsheet.get('sheets', []) if not sheet.get('properties', {}).get('hidden', False)]
                    if sheet_name not in sheets:
                        return jsonify({
                            'success': False, 
                            'error': f'Sheet "{sheet_name}" not found or is hidden',
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
                    'spreadsheet_url': spreadsheet_url,
                    'events': [],
                    'message': 'No data found in sheet',
                    'debug_logs': capture_handler.logs
                })

            # Parse the events
            try:
                events = parse_sports_events(values, sheet_name)
                    
                if not events:
                    return jsonify({
                        'success': True,
                        'spreadsheet_title': spreadsheet_title,
                        'spreadsheet_url': spreadsheet_url,
                        'events': [],
                        'message': 'No events found in sheet',
                        'parser_used': 'traditional',
                        'sheets': sheets,
                        'debug_logs': capture_handler.logs
                    })
                    
                return jsonify({
                    'success': True,
                    'spreadsheet_title': spreadsheet_title,
                    'spreadsheet_url': spreadsheet_url,
                    'events': events,
                    'parser_used': 'traditional',
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
        spreadsheet_id_val = data.get('spreadsheet_id')
        sheet_name = data.get('sheet_name')

        spreadsheet_id = resolve_spreadsheet_id(spreadsheet_id_val)

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
        logger.info("Using traditional parser")
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
            'parser_used': 'traditional'
        })

    except Exception as e:
        logger.error(f"Error in preview_changes: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@app.route('/preview_sheet_changes', methods=['POST'])
def preview_sheet_changes():
    """Calculate and return the changes for a single sheet without applying them."""
    logger.info("Starting preview_sheet_changes with logging")
    
    # Set up a log handler to capture logs for this request
    log_stream = io.StringIO()
    capture_handler = logging.StreamHandler(log_stream)
    capture_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    capture_handler.setFormatter(formatter)
    
    # Add the handler to the root logger to capture everything
    root_logger = logging.getLogger()
    root_logger.addHandler(capture_handler)

    try:
        data = request.get_json()
        spreadsheet_id_val = data.get('spreadsheet_id')
        sheet_name = data.get('sheet_name')

        spreadsheet_id = resolve_spreadsheet_id(spreadsheet_id_val)

        if not spreadsheet_id or not sheet_name:
            return jsonify({'success': False, 'error': 'Spreadsheet ID and sheet name are required'})

        service = get_calendar_service()
        sheets_service = get_sheets_service()

        # Get spreadsheet title and URL
        try:
            spreadsheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            spreadsheet_title = spreadsheet_metadata.get('properties', {}).get('title', 'Untitled Spreadsheet')
            spreadsheet_url = spreadsheet_metadata.get('spreadsheetUrl')
        except HttpError as e:
            logger.error(f"Error fetching spreadsheet metadata: {e}")
            spreadsheet_title = 'Untitled Spreadsheet'
            spreadsheet_url = '#'

        # Get sheet data and parse events
        values = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
        if not values:
            return jsonify({
                'success': True, 
                'changes': {'inserted': [], 'updated': [], 'deleted': []}, 
                'message': 'No data found in sheet',
                'spreadsheet_title': spreadsheet_title,
                'spreadsheet_url': spreadsheet_url
            })

        events = parse_sports_events(values, sheet_name)
        
        # Calculate stats
        stats = {
            'event_count': 0,
            'first_event_date': None,
            'last_event_date': None
        }
        if events:
            stats['event_count'] = len(events)
            dates = []
            for event in events:
                start = event.get('start', {})
                if 'dateTime' in start:
                    dates.append(parser.isoparse(start['dateTime']).date())
                elif 'date' in start:
                    dates.append(parser.isoparse(start['date']).date())
            
            logger.debug(f"Dates collected for stats: {[d.isoformat() for d in dates]}")

            if dates:
                stats['first_event_date'] = min(dates).isoformat()
                stats['last_event_date'] = max(dates).isoformat()
                logger.debug(f"Min date: {stats['first_event_date']}, Max date: {stats['last_event_date']}")

        # Get existing events
        calendar_name = f"SLOHS {sheet_name}"
        calendar_id = create_or_get_sports_calendar(service, calendar_name)
        existing_events_dict = get_existing_events(service, calendar_id)
        
        # Calculate changes
        changes = calculate_changes(events, existing_events_dict)
        
        log_contents = log_stream.getvalue()
        
        return jsonify({
            'success': True,
            'changes': changes,
            'logs': log_contents,
            'stats': stats,
            'spreadsheet_title': spreadsheet_title,
            'spreadsheet_url': spreadsheet_url
        })

    except Exception as e:
        logger.error(f"Error in preview_sheet_changes: {e}")
        logger.error(traceback.format_exc())
        log_contents = log_stream.getvalue()
        return jsonify({'success': False, 'error': str(e), 'logs': log_contents}), 500
    finally:
        root_logger.removeHandler(capture_handler)


@app.route('/apply_changes', methods=['POST'])
def apply_changes():
    """Apply changes for a single sheet and return detailed results, including logs."""
    logger.info("Starting apply_changes for a single sheet")
    
    # Set up a log handler to capture logs for this request
    log_stream = io.StringIO()
    capture_handler = logging.StreamHandler(log_stream)
    capture_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    capture_handler.setFormatter(formatter)
    
    # Add the handler to the root logger to capture everything
    root_logger = logging.getLogger()
    root_logger.addHandler(capture_handler)
    
    try:
        data = request.get_json()
        spreadsheet_id_val = data.get('spreadsheet_id')
        sheet_name = data.get('sheet_name')

        spreadsheet_id = resolve_spreadsheet_id(spreadsheet_id_val)

        if not spreadsheet_id or not sheet_name:
            return jsonify({'success': False, 'error': 'Spreadsheet ID and sheet name are required'})

        # Calendar name is always derived from the sheet name
        calendar_name = f"SLOHS {sheet_name}"

        logger.info(f"Applying changes for sheet: {sheet_name} to calendar: {calendar_name}")
        
        service = get_calendar_service()
        sheets_service = get_sheets_service()

        # Get sheet data and parse events
        values = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
        if not values:
            return jsonify({'success': False, 'error': 'No data found in sheet'})

        events = parse_sports_events(values, sheet_name)
        
        # Create or get calendar
        calendar_id = create_or_get_sports_calendar(service, calendar_name)
        
        # Update calendar and get detailed changes
        deleted, inserted, changed, details = update_calendar(service, events, calendar_id, return_detailed_changes=True)
        
        logger.info(f"Sync for {sheet_name} complete: {inserted} created, {changed} updated, {deleted} deleted.")
        
        # Get the logs
        log_contents = log_stream.getvalue()
        
        return jsonify({
            'success': True,
            'message': f"Sync for {sheet_name} complete.",
            'events_created': inserted,
            'events_updated': changed,
            'events_deleted': deleted,
            'details': details,
            'logs': log_contents
        })

    except Exception as e:
        logger.error(f"Error in apply_changes: {str(e)}")
        logger.error(traceback.format_exc())
        log_contents = log_stream.getvalue()
        return jsonify({'success': False, 'error': str(e), 'logs': log_contents}), 500
    finally:
        # Important: remove the handler to avoid logging to this stream in other requests
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
        spreadsheet_id_val = data.get('spreadsheet_id')
        spreadsheet_id = resolve_spreadsheet_id(spreadsheet_id_val)

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
                logger.info(f"Using traditional parser for {sheet_name}")
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
        spreadsheet_id_val = data.get('spreadsheet_id')
        spreadsheet_id = resolve_spreadsheet_id(spreadsheet_id_val)
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
        spreadsheet_id_val = data.get('spreadsheet_id')
        spreadsheet_id = resolve_spreadsheet_id(spreadsheet_id_val)
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
from automated_sync import main as run_automated_sync, run_automated_sync_stream
@app.route('/sync_all_sheets_stream')
def sync_all_sheets_stream():
    """Stream the sync process using Server-Sent Events."""
    def generate():
        for progress in run_automated_sync_stream():
            yield f"data: {progress}\n\n"
    return Response(generate(), mimetype='text/event-stream')


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
    """
    Triggers the automated sync process.
    This endpoint is designed for non-interactive use (e.g., Cloud Scheduler).
    """
    logger.info("trigger_sync called")
    logger.info("Sync triggered")
    try:
        logger.info("Calling run_automated_sync")
        run_automated_sync()
        logger.info("Automated sync process finished successfully.")
        return jsonify({'success': True, 'message': 'Sync triggered successfully!'})
    except Exception as e:
        logger.error(f"Error in trigger_sync: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=8080)