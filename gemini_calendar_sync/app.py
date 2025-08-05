from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.generativeai as genai
import os
import pickle
import json
import logging
import traceback
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('gemini_calendar_sync.log')
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

def get_google_credentials():
    """Get Google OAuth credentials."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

def get_sheets_service():
    """Get an authenticated Google Sheets service."""
    try:
        creds = get_google_credentials()
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error getting sheets service: {str(e)}")
        raise

def get_calendar_service():
    """Get an authenticated Google Calendar service."""
    try:
        creds = get_google_credentials()
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error getting calendar service: {str(e)}")
        raise

def parse_sheet_with_gemini(values):
    """Parse spreadsheet data using Gemini."""
    try:
        # Prepare the prompt for Gemini
        prompt = f"""
        Analyze this spreadsheet data and extract calendar events in JSON format.
        The first row contains the sport name, the second row contains headers, and subsequent rows contain event data.
        
        Required columns:
        - Date (required)
        - Event/Opponent (required)
        - Location (required)
        - Time (optional)
        - Transportation (optional)
        - Release Time (optional)
        - Departure Time (optional)
        - Attire (optional)
        - Notes (optional)
        - Bus (optional)
        - Vans (optional)
        
        Format each event as:
        {{
            "summary": "Sport Name: Event Name @ Location",
            "start": {{
                "dateTime": "ISO 8601 datetime",
                "timeZone": "America/Los_Angeles"
            }},
            "end": {{
                "dateTime": "ISO 8601 datetime",
                "timeZone": "America/Los_Angeles"
            }},
            "location": "location",
            "description": "Location: location\\nTime: time\\nTransportation: transportation\\nRelease Time: release_time\\nDeparture Time: departure_time\\nAttire: attire\\nNotes: notes\\nBus: bus\\nVans: vans",
            "transportation": "transportation value if available",
            "release_time": "release time value if available",
            "departure_time": "departure time value if available",
            "attire": "attire value if available",
            "notes": "notes value if available",
            "bus": "bus value if available",
            "vans": "vans value if available"
        }}
        
        Rules:
        1. First row is the sport name
        2. Second row contains headers
        3. Required columns (Date, Event/Opponent, Location) must be present
        4. If time is missing, create an all-day event using date format
        5. If time is provided, create a timed event with 2-hour duration
        6. Skip rows with missing required fields
        7. Use timezone America/Los_Angeles
        8. Convert dates to ISO 8601 format
        9. Include all available optional fields in description and as custom fields
        10. Skip invalid events but continue processing others
        
        Here's the spreadsheet data:
        {json.dumps(values)}
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the response
        try:
            events = json.loads(response.text)
            if not isinstance(events, list):
                events = [events]
            
            # Validate and clean events
            valid_events = []
            for event in events:
                try:
                    # Ensure required fields are present
                    if not all(key in event for key in ['summary', 'start', 'end', 'location']):
                        logger.warning(f"Skipping event missing required fields: {event}")
                        continue
                    
                    # Validate datetime format
                    try:
                        datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                        datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning(f"Skipping event with invalid datetime format: {event}")
                        continue
                    
                    valid_events.append(event)
                except Exception as e:
                    logger.warning(f"Error processing event: {str(e)}")
                    continue
            
            return valid_events
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Gemini response: {str(e)}")
            return []
    except Exception as e:
        logger.error(f"Error in parse_sheet_with_gemini: {str(e)}")
        logger.error(traceback.format_exc())
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth')
def auth():
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            SCOPES,
            redirect_uri=request.url_root.rstrip('/') + '/auth/callback'
        )
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return jsonify({'success': True, 'auth_url': auth_url})
    except Exception as e:
        logger.error(f"Error generating auth URL: {str(e)}")
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
            
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            SCOPES,
            redirect_uri=request.url_root.rstrip('/') + '/auth/callback'
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        
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
        data = request.get_json()
        spreadsheet_id = data.get('spreadsheet_id')
        sheet_name = data.get('sheet_name')

        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'Spreadsheet ID is required'}), 400

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
                        sheet_name = sheets[0]
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
            range_name = f'{sheet_name}!A:Z'
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

            # Parse the events using Gemini
            events = parse_sheet_with_gemini(values)
            
            if not events:
                return jsonify({
                    'success': True,
                    'spreadsheet_title': spreadsheet_title,
                    'events': [],
                    'message': 'No events found in sheet',
                    'sheets': sheets
                })
                
            return jsonify({
                'success': True,
                'spreadsheet_title': spreadsheet_title,
                'events': events,
                'sheets': sheets
            })

        except Exception as e:
            logger.error(f"Error in load_sheet: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'success': False, 'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Error in load_sheet route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/apply_changes', methods=['POST'])
def apply_changes():
    try:
        data = request.get_json()
        events = data.get('events', [])
        calendar_name = data.get('calendar_name', 'Sports Calendar')

        if not events:
            return jsonify({'success': False, 'error': 'No events to apply'}), 400

        try:
            # Get calendar service
            calendar_service = get_calendar_service()
            
            # Ensure calendar name has SLOHS prefix
            if not calendar_name.startswith('SLOHS '):
                calendar_name = f"SLOHS {calendar_name}"
            
            # Create or get calendar
            calendar = {
                'summary': calendar_name,
                'timeZone': 'America/Los_Angeles'
            }
            
            created_calendar = calendar_service.calendars().insert(body=calendar).execute()
            calendar_id = created_calendar['id']
            
            # Make the calendar world-readable by setting ACL
            try:
                acl_rule = {
                    'scope': {
                        'type': 'default'
                    },
                    'role': 'reader'
                }
                calendar_service.acl().insert(calendarId=calendar_id, body=acl_rule).execute()
                logger.info(f"Made calendar {calendar_name} world-readable")
            except Exception as e:
                logger.warning(f"Could not make calendar world-readable: {str(e)}")
            
            # Add events to calendar
            for event in events:
                calendar_service.events().insert(
                    calendarId=calendar_id,
                    body=event
                ).execute()
            
            return jsonify({
                'success': True,
                'message': f'Successfully added {len(events)} events to calendar',
                'calendar_id': calendar_id
            })

        except Exception as e:
            logger.error(f"Error applying changes: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'success': False, 'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Error in apply_changes route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout')
def logout():
    try:
        # Clear credentials from session
        session.pop('credentials', None)
        logger.info("User logged out successfully")
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True) 