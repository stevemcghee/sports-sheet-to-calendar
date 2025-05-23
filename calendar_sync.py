import os
from datetime import datetime, timedelta, time, date
from dateutil import parser
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import logging
import argparse
from dotenv import load_dotenv
from tqdm import tqdm
import sys
import io
import re
import calendar
from dataclasses import dataclass
import traceback
import pandas as pd

# Load environment variables
load_dotenv()

# Create a custom file-like object for tqdm
class TqdmToLogger(io.StringIO):
    def write(self, buf):
        if buf.rstrip():  # Don't log empty lines
            tqdm.write(buf, end='')
    
    def flush(self):
        pass

class ScrollingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []
        
        # Get terminal dimensions
        try:
            import shutil
            terminal_size = shutil.get_terminal_size()
            self.terminal_height = terminal_size.lines - 2  # Reserve space for progress bar
            self.terminal_width = terminal_size.columns
        except:
            self.terminal_height = 20  # Default height
            self.terminal_width = 80  # Default width
            
    def emit(self, record):
        msg = self.format(record)
        
        # Truncate message if it's too long
        if len(msg) > self.terminal_width:
            msg = msg[:self.terminal_width - 3] + "..."
            
        self.messages.append(msg)
        
        # Keep only the last N messages where N is terminal height
        if len(self.messages) > self.terminal_height:
            self.messages = self.messages[-self.terminal_height:]
            
        # Clear screen and move to top
        tqdm.write('\033[2J\033[H')
        
        # Print all messages
        for message in self.messages:
            tqdm.write(message)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to console
        logging.FileHandler('calendar_sync.log')  # Log to file
    ]
)
logger = logging.getLogger(__name__)

# Prevent logging from propagating to root logger
logger.propagate = False

# Prevent other loggers from writing to stdout/stderr
logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
logging.getLogger('google_auth_oauthlib.flow').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/calendar'
]

# OAuth configuration
OAUTH_PORT = 8081

# Default values from environment variables
DEFAULT_SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
DEFAULT_CALENDAR_NAME = os.getenv('CALENDAR_NAME')
DEFAULT_PROJECT_ID = os.getenv('PROJECT_ID')

@dataclass
class DateRange:
    start: date
    end: date

def get_google_credentials():
    """Get or refresh Google API credentials."""
    try:
        logger.debug("Starting credential retrieval process")
        creds = None
        
        if os.path.exists('token.pickle'):
            logger.debug("Found existing token.pickle file")
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
                logger.debug("Loaded credentials from token.pickle")
        
        if not creds or not creds.valid:
            logger.debug("Credentials are invalid or missing")
            if creds and creds.expired and creds.refresh_token:
                logger.debug("Attempting to refresh expired credentials")
                try:
                    creds.refresh(Request())
                    logger.debug("Successfully refreshed credentials")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {str(e)}")
                    logger.error(traceback.format_exc())
                    creds = None  # Force new OAuth flow
            
            if not creds:
                logger.debug("Starting new OAuth flow")
                try:
                    logger.debug("Loading credentials.json")
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    logger.debug("Generating authorization URL")
                    
                    # Generate authorization URL
                    auth_url, _ = flow.authorization_url(
                        access_type='offline',
                        include_granted_scopes='true'
                    )
                    
                    print("\nPlease go to this URL to authorize the application:")
                    print(auth_url)
                    print("\nAfter authorization, enter the code you received:")
                    code = input("Enter the authorization code: ").strip()
                    
                    # Exchange the code for credentials
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                    logger.debug("Successfully obtained credentials from authorization code")
                        
                except Exception as e:
                    logger.error(f"Error during OAuth flow: {str(e)}")
                    logger.error(traceback.format_exc())
                    raise
            
            logger.debug("Saving credentials to token.pickle")
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        logger.debug("Successfully retrieved valid credentials")
        return creds
    except Exception as e:
        logger.error(f"Error in get_google_credentials: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def get_spreadsheet_data(service, spreadsheet_id, sheet_name):
    """Fetch data from Google Sheets."""
    try:
        logger.debug(f"Fetching data from sheet: {sheet_name}")
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A:I'  # Adjust range to include all relevant columns
        ).execute()
        return result.get('values', [])
    except Exception as e:
        logger.error(f"Error fetching spreadsheet data: {str(e)}")
        raise

def parse_date(date_str):
    """Parse a date string in MM/DD/YYYY format."""
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y").date()
    except ValueError:
        # Try to extract a valid date from strings like "week of 4/28/2025"
        match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', date_str)
        if match:
            return datetime.strptime(match.group(1), "%m/%d/%Y").date()
        raise ValueError(f"Invalid date format: {date_str}")

def parse_time(time_str):
    """Parse time string and return a datetime.time object or None for all-day events."""
    if not time_str or time_str.lower() in ('tbd', 'all day', 'all-day') or looks_like_location(time_str):
        return None

    # Extract first time if multiple times are present (e.g., "2:00 dive, 3:00 swim")
    first_time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(?:am|pm)?', time_str.lower())
    if not first_time_match:
        return None

    hour = int(first_time_match.group(1))
    minute = int(first_time_match.group(2)) if first_time_match.group(2) else 0

    # Assume times between 1 and 11 are PM
    if 1 <= hour <= 11 and 'am' not in time_str.lower():
        hour += 12

    return datetime.time(hour=hour, minute=minute)

def parse_date_range(date_str):
    """Parse a date range string (e.g., '2/15-17/2025')."""
    match = re.match(r'(\d{1,2})/(\d{1,2})-(\d{1,2})/(\d{4})', date_str)
    if not match:
        raise ValueError(f"Invalid date range format: {date_str}")
        
    month, start_day, end_day, year = map(int, match.groups())
    start_date = datetime(year, month, start_day).date()
    end_date = datetime(year, month, end_day).date()
    return start_date, end_date

def format_date(date_str):
    """Format date string to YYYY-MM-DD format."""
    try:
        # Split the date string into month, day, and year
        parts = date_str.split('/')
        if len(parts) != 3:
            raise ValueError(f"Invalid date format: {date_str}")
        
        month, day, year = parts
        
        # Ensure month and day are two digits
        month = month.zfill(2)
        day = day.zfill(2)
        
        # Format as YYYY-MM-DD
        return f"{year}-{month}-{day}"
    except Exception as e:
        logging.error(f"Error formatting date {date_str}: {str(e)}")
        raise

def parse_single_time(time_str):
    """Parse a single time string into a datetime.time object."""
    time_str = time_str.strip().upper()

    # Handle "3 PM" format
    pm_match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(?:PM|AM)?$', time_str)
    if pm_match:
        hours = int(pm_match.group(1))
        minutes = int(pm_match.group(2)) if pm_match.group(2) else 0

        # Convert to 24-hour format if PM is specified
        if 'PM' in time_str and hours < 12:
            hours += 12
        elif 'AM' in time_str and hours == 12:
            hours = 0

        return datetime.time(hours, minutes)

    # Handle special cases like "TBD", "All Day", etc.
    if time_str.lower() in ('tbd', 'all day') or looks_like_location(time_str):
        return None

    raise ValueError(f"Invalid time format: {time_str}")

def looks_like_location(time_str):
    """Check if a string looks like a location rather than a time."""
    # Convert to lowercase for case-insensitive comparison
    time_str = time_str.lower()
    
    # List of common location keywords
    location_keywords = ['athletes', 'slohs', 'home', 'away', 'field', 'gym', 'stadium', 'court', 'pool']
    
    # Check if any location keyword is in the string
    return any(keyword in time_str for keyword in location_keywords)

def parse_time(time_str, date):
    """Parse time string into datetime object."""
    if not time_str or time_str.lower() == 'tbd' or looks_like_location(time_str):
        # For all-day events, start at midnight
        return date.replace(hour=0, minute=0, second=0)

    # Extract first time if multiple times are present
    first_time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM)?)', time_str)
    if first_time_match:
        time_str = first_time_match.group(1)
    
    time_obj = parse_single_time(time_str)
    if time_obj is None:
        # Handle case where parse_single_time returns None (TBD, All Day, etc.)
        return date.replace(hour=0, minute=0, second=0)
    
    return datetime.datetime.combine(date, time_obj)

def parse_sports_events(data, sheet_name=None):
    """Parse sports events from list data."""
    if not data or len(data) < 3:  # Need at least sport name, headers, and one event
        return []

    # Extract sport name from first row or use sheet_name
    sport_name = data[0][0].strip() if data[0][0].strip() else sheet_name

    # Get headers from second row
    headers = data[1]
    date_idx = headers.index("Date")
    event_idx = headers.index("Event")
    location_idx = headers.index("Location")
    time_idx = headers.index("Time")

    events = []
    for row in data[2:]:  # Skip sport name and headers
        try:
            date_str = row[date_idx]
            event = row[event_idx]
            location = row[location_idx]
            time_str = row[time_idx] if len(row) > time_idx else ""

            # Handle date ranges (e.g., "2/15-17/2025")
            if "-" in date_str and "/" in date_str:
                start_date, end_date = parse_date_range(date_str)
            else:
                try:
                    start_date = parse_date(date_str)
                    end_date = start_date
                except ValueError:
                    continue  # Skip invalid dates

            # Parse time and determine if all-day event
            parsed_time = parse_time(time_str)
            is_all_day = parsed_time is None

            # Format event
            event_dict = {
                "summary": f"{sport_name}: {event} @ {location}",
                "description": f"Time: {'TBD' if is_all_day else time_str}",
                "location": location,
            }

            # Set start and end times based on whether it's an all-day event
            if is_all_day:
                # All-day events: start at midnight of start date, end at midnight of next day
                event_dict["start"] = start_date.strftime("%Y-%m-%d")
                event_dict["end"] = (end_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                # Timed events: use parsed time for start, add 2 hours for end
                start_datetime = datetime.datetime.combine(start_date, parsed_time)
                end_datetime = start_datetime + datetime.timedelta(hours=2)
                event_dict["start"] = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")
                event_dict["end"] = end_datetime.strftime("%Y-%m-%dT%H:%M:%S")

            events.append(event_dict)
        except (ValueError, IndexError) as e:
            continue  # Skip invalid rows

    return events

def list_available_sheets(service, spreadsheet_id):
    """List all available sheets in the spreadsheet."""
    try:
        logger.debug("Fetching available sheets")
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        logger.info("Available sheets:")
        for sheet in sheets:
            logger.info(f"- {sheet['properties']['title']}")
        return [sheet['properties']['title'] for sheet in sheets]
    except Exception as e:
        logger.error(f"Error listing sheets: {str(e)}")
        raise

def create_or_get_sports_calendar(service, calendar_name, description=None):
    """Create a new calendar if it doesn't exist, or get the existing one."""
    try:
        logger.debug(f"Checking for existing calendar: {calendar_name}")
        calendar_list = service.calendarList().list().execute()
        for calendar in calendar_list.get('items', []):
            if calendar['summary'] == calendar_name:
                logger.info(f"Found existing calendar: {calendar_name}")
                return calendar['id']
        
        logger.info(f"Creating new calendar: {calendar_name}")
        calendar = {
            'summary': calendar_name,
            'description': description or f'San Luis Obispo High School {calendar_name} Schedule',
            'accessRole': 'reader',  # Make calendar public
            'selected': True  # Show in calendar list by default
        }
        created_calendar = service.calendars().insert(body=calendar).execute()
        logger.info(f"Created new calendar with ID: {created_calendar['id']}")
        return created_calendar['id']
    except Exception as e:
        logger.error(f"Error creating/getting calendar {calendar_name}: {str(e)}")
        raise

def main():
    try:
        # Set up argument parser
        parser = argparse.ArgumentParser(description='Sync sports events from Google Sheets to Google Calendar')
        parser.add_argument('--spreadsheet-id', default=DEFAULT_SPREADSHEET_ID,
                          help=f'Google Spreadsheet ID (default: {DEFAULT_SPREADSHEET_ID})')
        parser.add_argument('--calendar-name', default=DEFAULT_CALENDAR_NAME,
                          help=f'Calendar name (default: {DEFAULT_CALENDAR_NAME})')
        parser.add_argument('--project-id', default=DEFAULT_PROJECT_ID,
                          help=f'Google Cloud Project ID (default: {DEFAULT_PROJECT_ID})')
        parser.add_argument('--wipe', action='store_true',
                          help='Wipe all events from calendars before syncing')
        args = parser.parse_args()

        logger.info("Starting calendar sync")
        logger.debug(f"Using spreadsheet ID: {args.spreadsheet_id}")
        logger.debug(f"Using calendar name: {args.calendar_name}")
        logger.debug(f"Using project ID: {args.project_id}")
        logger.debug(f"Wipe mode: {args.wipe}")
        
        # Get credentials and build services
        logger.debug("Getting Google credentials")
        creds = get_google_credentials()
        logger.debug("Building Google services")
        sheets_service = build('sheets', 'v4', credentials=creds)
        calendar_service = build('calendar', 'v3', credentials=creds)
        
        # Create or get main sports calendar
        logger.debug("Getting main calendar")
        main_calendar_id = create_or_get_sports_calendar(calendar_service, args.calendar_name)
        logger.info(f"Using main calendar ID: {main_calendar_id}")
        
        # If wipe mode is enabled, delete all events from main calendar
        if args.wipe:
            logger.info("Wipe mode enabled - deleting all events from main calendar")
            delete_all_events(calendar_service, main_calendar_id)
        
        # List available sheets
        logger.debug("Listing available sheets")
        available_sheets = list_available_sheets(sheets_service, args.spreadsheet_id)
        
        if not available_sheets:
            raise ValueError("No sheets found in the spreadsheet")
            
        # Track events per sport for summary
        sport_event_counts = {}
        total_events = 0
        all_events = []  # Collect all events for main calendar
        
        # Track total operations across all calendars
        total_deleted = 0
        total_inserted = 0
        total_changed = 0
        
        # First pass to count total events for progress bar
        logger.debug("Counting total events for progress estimation...")
        total_sheets = len(available_sheets)
        total_events_estimate = 0
        for sheet_name in available_sheets:
            data = get_spreadsheet_data(sheets_service, args.spreadsheet_id, sheet_name)
            # Estimate 1 event per non-empty row after header
            total_events_estimate += len([row for row in data[2:] if row and len(row) >= 5])
            
        # Calculate total operations: sheets processing + event creation + main calendar update
        total_operations = total_sheets + total_events_estimate + 1
        
        # Create progress bar
        pbar = tqdm(total=total_operations, desc="Overall Progress", unit="op")
        
        # Process each sheet
        for sheet_name in available_sheets:
            logger.info(f"Processing sheet: {sheet_name}")
            
            # Get spreadsheet data
            logger.debug(f"Fetching data from sheet: {sheet_name}")
            data = get_spreadsheet_data(sheets_service, args.spreadsheet_id, sheet_name)
            pbar.update(1)
            
            # Parse events
            logger.debug(f"Parsing sports events from {sheet_name}")
            events = parse_sports_events(data, sheet_name)
            
            if events:
                # Get sport name from first event
                sport_name = events[0]['summary']
                sport_event_counts[sport_name] = len(events)
                total_events += len(events)
                
                # Add events to main calendar collection
                all_events.extend(events)
                
                # Create or get sport-specific calendar
                sport_calendar_id = create_or_get_sports_calendar(
                    calendar_service, 
                    f"SLOHS {sport_name}",
                    f'San Luis Obispo High School {sport_name} Schedule'
                )
                
                # If wipe mode is enabled, delete all events from sport calendar
                if args.wipe:
                    logger.info(f"Wipe mode enabled - deleting all events from {sport_name} calendar")
                    delete_all_events(calendar_service, sport_calendar_id)
                
                # Update sport-specific calendar
                logger.debug(f"Updating {sport_name} calendar with events")
                deleted, inserted, changed = update_calendar(calendar_service, events, sport_calendar_id)
                total_deleted += deleted
                total_inserted += inserted
                total_changed += changed
                pbar.update(len(events))
            
            logger.info(f"Completed processing sheet: {sheet_name}")
        
        # Update main calendar with all events
        if all_events:
            logger.debug("Updating main calendar with all events")
            deleted, inserted, changed = update_calendar(calendar_service, all_events, main_calendar_id)
            total_deleted += deleted
            total_inserted += inserted
            total_changed += changed
            pbar.update(1)  # Final update for main calendar
            
        # Close the progress bar
        pbar.close()
            
        # Print summary
        logger.info("\n=== Calendar Sync Summary ===")
        logger.info(f"Total sports processed: {len(sport_event_counts)}")
        logger.info(f"Total events created: {total_events}")
        logger.info("\nEvents per sport:")
        for sport, count in sport_event_counts.items():
            logger.info(f"- {sport}: {count} events")
        logger.info("\nCalendar Operations:")
        logger.info(f"- Events deleted: {total_deleted}")
        logger.info(f"- Events inserted: {total_inserted}")
        logger.info(f"- Events changed: {total_changed}")
        logger.info("===========================\n")
            
        logger.debug("Calendar sync completed successfully for all sheets")
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        raise

def delete_all_events(service, calendar_id):
    """Delete all events from the specified calendar."""
    try:
        # Get all events with pagination
        logger.debug("Fetching all events from calendar")
        events = []
        page_token = None
        
        while True:
            events_result = service.events().list(
                calendarId=calendar_id,
                pageToken=page_token,
                maxResults=2500  # Maximum allowed by API
            ).execute()
            
            page_events = events_result.get('items', [])
            events.extend(page_events)
            
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
                
        # Delete each event
        total_events = len(events)
        logger.info(f"Found {total_events} events to delete")
        
        for event in events:
            logger.debug(f"Deleting event: {event.get('summary', 'No title')}")
            service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
            
        logger.info("Successfully deleted all events from calendar")
    except Exception as e:
        logger.error(f"Error deleting events: {str(e)}")
        raise

def get_event_key(event):
    """Generate a unique key for an event based on its start/end times and summary."""
    start = event.get('start', {})
    end = event.get('end', {})
    summary = event.get('summary', '')
    
    # Get start time/date
    if 'dateTime' in start:
        # For datetime events, keep the full datetime string
        start_str = start['dateTime']
    elif 'date' in start:
        start_str = start['date']
    else:
        return None
        
    # Get end time/date
    if 'dateTime' in end:
        # For datetime events, keep the full datetime string
        end_str = end['dateTime']
    elif 'date' in end:
        end_str = end['date']
    else:
        return None
        
    return f"{start_str}_{end_str}_{summary}"

def events_are_equal(event1, event2):
    """Compare two events for equality, ignoring timezone differences and handling missing fields."""
    # Compare summaries (ignoring whitespace)
    summary1 = event1.get('summary', '').strip()
    summary2 = event2.get('summary', '').strip()
    if summary1 != summary2:
        return False
        
    # Compare start times
    start1 = event1.get('start', {})
    start2 = event2.get('start', {})
    
    # Handle datetime vs date comparison
    if 'dateTime' in start1 and 'dateTime' in start2:
        # Strip timezone for comparison
        date1 = re.sub(r'[+-]\d{2}:\d{2}$', '', start1['dateTime'])
        date2 = re.sub(r'[+-]\d{2}:\d{2}$', '', start2['dateTime'])
        if date1 != date2:
            return False
    elif 'date' in start1 and 'date' in start2:
        if start1['date'] != start2['date']:
            return False
    else:
        # One is date and one is datetime - compare just the date portion
        date1 = start1.get('date') or start1['dateTime'].split('T')[0]
        date2 = start2.get('date') or start2['dateTime'].split('T')[0]
        if date1 != date2:
            return False
        
    # Compare end times
    end1 = event1.get('end', {})
    end2 = event2.get('end', {})
    
    # Handle datetime vs date comparison
    if 'dateTime' in end1 and 'dateTime' in end2:
        # Strip timezone for comparison
        date1 = re.sub(r'[+-]\d{2}:\d{2}$', '', end1['dateTime'])
        date2 = re.sub(r'[+-]\d{2}:\d{2}$', '', end2['dateTime'])
        if date1 != date2:
            return False
    elif 'date' in end1 and 'date' in end2:
        if end1['date'] != end2['date']:
            return False
    else:
        # One is date and one is datetime - compare just the date portion
        date1 = end1.get('date') or end1['dateTime'].split('T')[0]
        date2 = end2.get('date') or end2['dateTime'].split('T')[0]
        if date1 != date2:
            return False
        
    # Compare descriptions (ignoring whitespace and timezone info)
    # Handle None descriptions as empty strings
    desc1 = (event1.get('description') or '').strip()
    desc2 = (event2.get('description') or '').strip()
    
    # Clean up descriptions by removing timezone info and whitespace
    desc1 = re.sub(r'[+-]\d{2}:\d{2}', '', desc1).strip()
    desc2 = re.sub(r'[+-]\d{2}:\d{2}', '', desc2).strip()
    
    return desc1 == desc2

def get_existing_events(service, calendar_id):
    """Get all existing events from the calendar and index them by key."""
    try:
        events = {}
        page_token = None
        
        while True:
            events_result = service.events().list(
                calendarId=calendar_id,
                pageToken=page_token,
                maxResults=2500
            ).execute()
            
            for event in events_result.get('items', []):
                key = get_event_key(event)
                events[key] = event
            
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
                
        return events
    except Exception as e:
        logger.error(f"Error fetching existing events: {str(e)}")
        raise

def update_calendar(service, events, calendar_id):
    """Update calendar with new events."""
    try:
        logger.info("Starting calendar update")
        logger.info(f"Processing {len(events)} events for calendar {calendar_id}")
        
        # Get existing events
        existing_events = get_existing_events(service, calendar_id)
        logger.info(f"Found {len(existing_events)} existing events")
        
        # Convert existing events to list if it's a dictionary
        if isinstance(existing_events, dict):
            logger.debug("Converting existing events from dict to list")
            existing_events = list(existing_events.values())
        
        # Create a dictionary of existing events for easy lookup
        existing_events_dict = {}
        for event in existing_events:
            try:
                if not isinstance(event, dict):
                    logger.error(f"Invalid event format in existing events: {event}")
                    continue
                    
                if 'start' not in event or 'end' not in event:
                    logger.error(f"Event missing start/end times: {event}")
                    continue
                    
                if not isinstance(event['start'], dict) or not isinstance(event['end'], dict):
                    logger.error(f"Invalid start/end format in event: {event}")
                    logger.error(f"Start type: {type(event['start'])}")
                    logger.error(f"End type: {type(event['end'])}")
                    continue
                    
                if 'dateTime' not in event['start'] or 'dateTime' not in event['end']:
                    logger.error(f"Event missing dateTime in start/end: {event}")
                    logger.error(f"Start: {event['start']}")
                    logger.error(f"End: {event['end']}")
                    continue
                    
                event_key = get_event_key(event)
                existing_events_dict[event_key] = event
                logger.debug(f"Added existing event to dictionary: {event_key}")
            except Exception as e:
                logger.error(f"Error processing existing event: {str(e)}")
                logger.error(f"Event data: {event}")
                logger.error(traceback.format_exc())
                continue
        
        # Process each event
        events_to_keep = set()
        events_to_delete = set()
        events_to_insert = []
        events_to_change = []
        
        for i, event in enumerate(events):
            try:
                logger.debug(f"\nProcessing event {i+1}/{len(events)}")
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
                    logger.error(f"Start type: {type(event['start'])}")
                    logger.error(f"End type: {type(event['end'])}")
                    continue
                    
                if 'dateTime' not in event['start'] or 'dateTime' not in event['end']:
                    logger.error(f"Event missing dateTime in start/end: {event}")
                    logger.error(f"Start: {event['start']}")
                    logger.error(f"End: {event['end']}")
                    continue
                
                event_key = get_event_key(event)
                logger.debug(f"Generated event key: {event_key}")
                
                if event_key in existing_events_dict:
                    logger.debug(f"Found existing event with key: {event_key}")
                    existing_event = existing_events_dict[event_key]
                    
                    if not events_are_equal(event, existing_event):
                        logger.debug(f"Event needs update: {event_key}")
                        events_to_change.append(event)
                    else:
                        logger.debug(f"Event unchanged: {event_key}")
                        events_to_keep.add(event_key)
                else:
                    logger.debug(f"New event: {event_key}")
                    events_to_insert.append(event)
                    
            except Exception as e:
                logger.error(f"Error processing event {i+1}: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Event data: {event}")
                logger.error(traceback.format_exc())
                continue
        
        # Find events to delete
        for event_key in existing_events_dict:
            if event_key not in events_to_keep:
                logger.debug(f"Event to delete: {event_key}")
                events_to_delete.add(event_key)
        
        # Apply changes
        logger.info(f"Applying changes: {len(events_to_insert)} to insert, {len(events_to_change)} to update, {len(events_to_delete)} to delete")
        
        # Delete events
        for event_key in events_to_delete:
            try:
                event = existing_events_dict[event_key]
                logger.debug(f"Deleting event: {event_key}")
                service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
            except Exception as e:
                logger.error(f"Error deleting event {event_key}: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Insert new events
        for event in events_to_insert:
            try:
                logger.debug(f"Inserting event: {event['summary']}")
                service.events().insert(calendarId=calendar_id, body=event).execute()
            except Exception as e:
                logger.error(f"Error inserting event: {str(e)}")
                logger.error(f"Event data: {event}")
                logger.error(traceback.format_exc())
        
        # Update changed events
        for event in events_to_change:
            try:
                event_key = get_event_key(event)
                existing_event = existing_events_dict[event_key]
                logger.debug(f"Updating event: {event_key}")
                service.events().update(calendarId=calendar_id, eventId=existing_event['id'], body=event).execute()
            except Exception as e:
                logger.error(f"Error updating event {event_key}: {str(e)}")
                logger.error(f"Event data: {event}")
                logger.error(traceback.format_exc())
        
        logger.info("Calendar update completed successfully")
        
    except Exception as e:
        logger.error(f"Error in update_calendar: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == '__main__':
    main() 