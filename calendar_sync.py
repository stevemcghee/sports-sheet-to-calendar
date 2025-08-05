import os
from datetime import datetime, timedelta, time as dtime, date
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
    """Parse a date string in MM/DD/YYYY format, or a range like 2/15-17/2025.
    Returns (start_date, end_date) where end_date may be None for single dates."""
    date_str = date_str.strip()
    logger.debug(f"Parsing date string: '{date_str}'")
    
    # Reject invalid formats like "week of" or "or"
    if 'week of' in date_str.lower() or ' or ' in date_str.lower():
        logger.debug(f"Rejecting date with invalid keywords: '{date_str}'")
        raise ValueError(f"Invalid date format: {date_str}")
    
    # Handle date ranges like 2/15-17/2025
    range_match = re.match(r'(\d{1,2})/(\d{1,2})-(\d{1,2})/(\d{4})', date_str)
    if range_match:
        month, start_day, end_day, year = map(int, range_match.groups())
        start_date = datetime(year, month, start_day).date()
        end_date = datetime(year, month, end_day).date()
        logger.debug(f"Parsed date range: {start_date} to {end_date}")
        return start_date, end_date
    # Handle date ranges like 4/16-18/2025 (shorthand, no month on end)
    shorthand_match = re.match(r'(\d{1,2})/(\d{1,2})-(\d{1,2})/(\d{4})', date_str)
    if shorthand_match:
        month, start_day, end_day, year = map(int, shorthand_match.groups())
        start_date = datetime(year, month, start_day).date()
        end_date = datetime(year, month, end_day).date()
        logger.debug(f"Parsed shorthand date range: {start_date} to {end_date}")
        return start_date, end_date
    # Handle normal MM/DD/YYYY or MM/DD/YY
    try:
        # First try MM/DD/YYYY format
        d = datetime.strptime(date_str, "%m/%d/%Y").date()
        logger.debug(f"Parsed single date: {d}")
        return d, None
    except ValueError:
        try:
            # Try MM/DD/YY format (2-digit year)
            d = datetime.strptime(date_str, "%m/%d/%y").date()
            logger.debug(f"Parsed single date (2-digit year): {d}")
            return d, None
        except Exception as e:
            logger.debug(f"Failed to parse date '{date_str}': {str(e)}")
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

    return dtime(hour=hour, minute=minute)

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
    # Handle 'TBD', 'All Day', etc.
    if time_str.lower() in ('tbd', 'all day') or looks_like_location(time_str):
        return None
    # Handle '3 PM', '3:00 PM', '15:00', etc.
    pm_match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$', time_str)
    if pm_match:
        hours = int(pm_match.group(1))
        minutes = int(pm_match.group(2)) if pm_match.group(2) else 0
        ampm = pm_match.group(3)
        if ampm == 'PM' and hours < 12:
            hours += 12
        elif ampm == 'AM' and hours == 12:
            hours = 0
        return dtime(hours, minutes)
    # Handle 24-hour time
    twentyfour_match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
    if twentyfour_match:
        hours = int(twentyfour_match.group(1))
        minutes = int(twentyfour_match.group(2))
        return dtime(hours, minutes)
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
        return datetime.combine(date, dtime(0, 0, 0))
    # Extract first time if multiple times are present
    first_time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM)?)', time_str)
    if first_time_match:
        time_str = first_time_match.group(1)
    time_obj = parse_single_time(time_str)
    if time_obj is None:
        return datetime.combine(date, dtime(0, 0, 0))
    return datetime.combine(date, time_obj)

def extract_first_time(time_str):
    """Extract the first valid time from a string like '2:00 dive, 3:00 swim'."""
    if not time_str:
        logger.debug("No time string provided")
        return None
    # Find all time-like patterns
    matches = re.findall(r'(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)?', time_str)
    logger.debug(f"Time string '{time_str}' - found {len(matches)} time matches: {matches}")
    if matches:
        hour, minute, ampm = matches[0]
        hour = int(hour)
        minute = int(minute) if minute else 0
        if ampm and ampm.lower() == 'pm' and hour < 12:
            hour += 12
        elif ampm and ampm.lower() == 'am' and hour == 12:
            hour = 0
        # Default to PM for times between 1-11 if no AM/PM specified
        elif not ampm and 1 <= hour <= 11:
            hour += 12
        result = dtime(hour, minute)
        logger.debug(f"Parsed time: {result}")
        return result
    logger.debug(f"No valid time found in '{time_str}'")
    return None

def parse_sports_events(data, sheet_name=None):
    """Parse sports events from list data."""
    if not data or len(data) < 2:  # Need at least headers and one event
        logger.warning(f"Not enough data rows: {len(data) if data else 0}")
        return []

    # Find the header row by looking for a row that contains date-related keywords
    header_row_idx = None
    sport_name = sheet_name  # Default to sheet name
    
    for i, row in enumerate(data):
        if not row:  # Skip empty rows
            continue
            
        # Check if this row looks like headers (contains date-related keywords)
        row_text = ' '.join(str(cell) for cell in row).lower()
        if any(keyword in row_text for keyword in ['date', 'event', 'location', 'time', 'venue', 'place']):
            header_row_idx = i
            # Look for sport name in earlier rows
            for j in range(i-1, -1, -1):
                if data[j] and data[j][0]:
                    potential_sport = data[j][0].strip()
                    # Check if this looks like a sport name (not coach info, not disclaimer)
                    if potential_sport and not any(keyword in potential_sport.lower() for keyword in ['coach', 'tentative', 'schedule', 'call']):
                        sport_name = potential_sport
                        break
            break
    
    if header_row_idx is None:
        logger.error("Could not find header row in data")
        logger.debug(f"Data rows: {[row[:3] if row else [] for row in data[:5]]}")  # Show first 5 rows
        return []
    
    headers = data[header_row_idx]
    logger.debug(f"Found headers at row {header_row_idx}: {headers}")
    logger.debug(f"Sport name: {sport_name}")
    
    # More flexible column detection
    date_idx = None
    event_idx = None
    location_idx = None
    time_idx = None
    
    for i, header in enumerate(headers):
        header_lower = str(header).lower().strip()
        if 'date' in header_lower:
            date_idx = i
        elif 'event' in header_lower or 'title' in header_lower or 'name' in header_lower or 'opponent' in header_lower:
            event_idx = i
        elif 'location' in header_lower or 'place' in header_lower or 'venue' in header_lower:
            location_idx = i
        elif 'time' in header_lower:
            # Prefer "Start Time" over other time columns
            if 'start' in header_lower:
                time_idx = i
            elif time_idx is None:  # Only set if no start time found yet
                time_idx = i
    
    logger.debug(f"Column indices - Date: {date_idx}, Event: {event_idx}, Location: {location_idx}, Time: {time_idx}")
    
    if date_idx is None or event_idx is None or location_idx is None:
        logger.error(f"Missing required columns. Found headers: {headers}")
        logger.error(f"Date column: {'found' if date_idx is not None else 'missing'}")
        logger.error(f"Event column: {'found' if event_idx is not None else 'missing'}")
        logger.error(f"Location column: {'found' if location_idx is not None else 'missing'}")
        return []
    
    # Time column is optional (for all-day events)
    if time_idx is None:
        logger.info("No time column found - will create all-day events")

    events = []
    data_start_row = header_row_idx + 1
    logger.debug(f"Processing {len(data[data_start_row:])} data rows starting from row {data_start_row}")
    for i, row in enumerate(data[data_start_row:]):
        try:
            # Check if we have enough columns for required fields
            required_max = max(date_idx, event_idx, location_idx)
            if len(row) < required_max + 1:
                logger.debug(f"Row {i+data_start_row+1} too short: {len(row)} columns, need at least {required_max + 1}")
                continue
                
            date_str = row[date_idx]
            event = row[event_idx]
            location = row[location_idx]
            time_str = row[time_idx] if time_idx is not None and len(row) > time_idx else ""
            
            logger.debug(f"Row {i+data_start_row+1}: Date='{date_str}', Event='{event}', Location='{location}', Time='{time_str}'")
            
            if not date_str or not event or not location:
                logger.debug(f"Row {i+data_start_row+1} missing required data - skipping")
                continue
            try:
                start_date, end_date = parse_date(date_str)
                # If end_date is None, it's a single-day event
                # If end_date is not None, it's a range (inclusive)
                # For all-day events, start at 00:00, end at 00:00 of the day after the end date
                parsed_time = extract_first_time(time_str)
                # New: extract last time if multiple times are present
                def extract_last_time(time_str):
                    if not time_str:
                        return None
                    matches = re.findall(r'(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)?', time_str)
                    if matches:
                        hour, minute, ampm = matches[-1]
                        hour = int(hour)
                        minute = int(minute) if minute else 0
                        if ampm and ampm.lower() == 'pm' and hour < 12:
                            hour += 12
                        elif ampm and ampm.lower() == 'am' and hour == 12:
                            hour = 0
                        elif not ampm and 1 <= hour <= 11:
                            hour += 12
                        return dtime(hour, minute)
                    return None
                # For sports events, always create all-day events for consistency
                if end_date:
                    # Multi-day event (inclusive range)
                    end_date_for_calendar = end_date + timedelta(days=1)  # Google Calendar end date is exclusive
                else:
                    # Single-day event
                    end_date_for_calendar = start_date + timedelta(days=1)  # Google Calendar end date is exclusive
                
                # Include time information in description if available
                description = f"Location: {location}"
                if parsed_time:
                    description += f"\nTime: {time_str}"
                
                event_dict = {
                    "summary": f"{sport_name} - {event} at {location}",
                    "description": description,
                    "location": location,
                    "start": {
                        "date": start_date.strftime("%Y-%m-%d")
                    },
                    "end": {
                        "date": end_date_for_calendar.strftime("%Y-%m-%d")
                    }
                }
                events.append(event_dict)
                logger.debug(f"Successfully created event: {event_dict['summary']}")
            except Exception as e:
                logger.error(f"Error parsing row {i+data_start_row+1}: {str(e)}")
                logger.error(f"Row data: {row}")
                continue
        except Exception as e:
            logger.error(f"Error processing row {i+data_start_row+1}: {str(e)}")
            continue
    
    logger.info(f"Successfully parsed {len(events)} events from {len(data[data_start_row:])} rows")
    
    # Log details about each event for debugging
    for i, event in enumerate(events):
        logger.debug(f"Event {i+1}: {event.get('summary', 'No summary')} at {event.get('location', 'No location')}")
    
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
            'selected': True  # Show in calendar list by default
        }
        created_calendar = service.calendars().insert(body=calendar).execute()
        calendar_id = created_calendar['id']
        logger.info(f"Created new calendar with ID: {calendar_id}")
        
        # Make the calendar world-readable by setting ACL
        try:
            acl_rule = {
                'scope': {
                    'type': 'default'
                },
                'role': 'reader'
            }
            service.acl().insert(calendarId=calendar_id, body=acl_rule).execute()
            logger.info(f"Made calendar {calendar_name} world-readable")
        except Exception as e:
            logger.warning(f"Could not make calendar world-readable: {str(e)}")
        
        return calendar_id
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
                # Use sheet name as sport name instead of extracting from event summary
                sport_name = sheet_name
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

def validate_event_times(event):
    """Validate that an event has valid start and end times."""
    try:
        start = event.get('start', {})
        end = event.get('end', {})
        
        # Check if both start and end are present
        if not start or not end:
            return False, "Missing start or end time"
            
        # Check if both are dictionaries
        if not isinstance(start, dict) or not isinstance(end, dict):
            return False, "Start and end must be dictionaries"
            
        # Get start time/date
        start_time = None
        if 'dateTime' in start:
            start_time = start['dateTime']
        elif 'date' in start:
            start_time = start['date']
        else:
            return False, "Start time missing dateTime or date"
            
        # Get end time/date
        end_time = None
        if 'dateTime' in end:
            end_time = end['dateTime']
        elif 'date' in end:
            end_time = end['date']
        else:
            return False, "End time missing dateTime or date"
            
        # For datetime events, check that end is after start
        if 'dateTime' in start and 'dateTime' in end:
            from datetime import datetime
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                if end_dt <= start_dt:
                    return False, f"End time ({end_time}) must be after start time ({start_time})"
            except ValueError as e:
                return False, f"Invalid datetime format: {str(e)}"
                
        # For date events, check that end is after or equal to start
        elif 'date' in start and 'date' in end:
            if end_time < start_time:
                return False, f"End date ({end_time}) must be after or equal to start date ({start_time})"
                
        return True, "Valid"
        
    except Exception as e:
        return False, f"Error validating times: {str(e)}"

def fix_event_times(event):
    """Attempt to fix common time issues in events."""
    try:
        start = event.get('start', {})
        end = event.get('end', {})
        
        # Only fix datetime events
        if 'dateTime' in start and 'dateTime' in end:
            from datetime import datetime, timedelta
            
            start_time = start['dateTime']
            end_time = end['dateTime']
            
            # Parse times
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # If end is before or equal to start, fix it
            if end_dt <= start_dt:
                # Add 1 hour to end time if it's the same as start
                if end_dt == start_dt:
                    end_dt = start_dt + timedelta(hours=1)
                else:
                    # If end is before start, swap them
                    start_dt, end_dt = end_dt, start_dt
                
                # Update the event
                start['dateTime'] = start_dt.isoformat()
                end['dateTime'] = end_dt.isoformat()
                
                return True, f"Fixed time range: {start_time} -> {start['dateTime']}, {end_time} -> {end['dateTime']}"
        
        return False, "No fixes needed"
        
    except Exception as e:
        return False, f"Error fixing times: {str(e)}"

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
                    
                # Check for either dateTime or date fields (handle both timed and all-day events)
                if ('dateTime' not in event['start'] and 'date' not in event['start']) or ('dateTime' not in event['end'] and 'date' not in event['end']):
                    logger.error(f"Event missing dateTime or date in start/end: {event}")
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
        
        logger.info(f"Processing {len(events)} events for calendar update")
        for i, event in enumerate(events):
            try:
                logger.info(f"Processing event {i+1}/{len(events)}: {event.get('summary', 'Unknown')}")
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
                    
                # Check for either dateTime or date fields (handle both timed and all-day events)
                if ('dateTime' not in event['start'] and 'date' not in event['start']) or ('dateTime' not in event['end'] and 'date' not in event['end']):
                    logger.error(f"❌ Event missing dateTime or date in start/end: {event}")
                    logger.error(f"Start: {event['start']}")
                    logger.error(f"End: {event['end']}")
                    continue
                
                # Validate event times
                is_valid, error_msg = validate_event_times(event)
                if not is_valid:
                    logger.warning(f"⚠️ Invalid event times for '{event.get('summary', 'Unknown')}': {error_msg}")
                    logger.warning(f"Attempting to fix time issues...")
                    
                    # Try to fix the time issues
                    fixed, fix_msg = fix_event_times(event)
                    if fixed:
                        logger.info(f"🔧 Fixed event times: {fix_msg}")
                        # Re-validate after fixing
                        is_valid, error_msg = validate_event_times(event)
                        if not is_valid:
                            logger.error(f"❌ Still invalid after fixing: {error_msg}")
                            logger.error(f"Event data: {event}")
                            continue
                    else:
                        logger.error(f"❌ Could not fix time issues: {fix_msg}")
                        logger.error(f"Event data: {event}")
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
        logger.info(f"Events to insert: {[event.get('summary', 'Unknown') for event in events_to_insert]}")
        logger.info(f"Events to update: {[event.get('summary', 'Unknown') for event in events_to_change]}")
        logger.info(f"Events to delete: {[existing_events_dict[key].get('summary', 'Unknown') for key in events_to_delete]}")
        

        
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
        logger.info(f"Inserting {len(events_to_insert)} new events")
        for i, event in enumerate(events_to_insert):
            try:
                logger.info(f"Inserting event {i+1}/{len(events_to_insert)}: {event['summary']}")
                logger.debug(f"Event details: {event}")
                
                # Validate event times before inserting
                is_valid, error_msg = validate_event_times(event)
                if not is_valid:
                    logger.warning(f"⚠️ Invalid event times for '{event.get('summary', 'Unknown')}': {error_msg}")
                    logger.warning(f"Attempting to fix time issues...")
                    
                    # Try to fix the time issues
                    fixed, fix_msg = fix_event_times(event)
                    if fixed:
                        logger.info(f"🔧 Fixed event times: {fix_msg}")
                        # Re-validate after fixing
                        is_valid, error_msg = validate_event_times(event)
                        if not is_valid:
                            logger.error(f"❌ Still invalid after fixing: {error_msg}")
                            logger.error(f"Event data: {event}")
                            continue
                    else:
                        logger.error(f"❌ Could not fix time issues: {fix_msg}")
                        logger.error(f"Event data: {event}")
                        continue
                
                # Insert the event
                result = service.events().insert(calendarId=calendar_id, body=event).execute()
                logger.info(f"✅ Successfully inserted event: {result.get('id', 'unknown')}")
                logger.debug(f"Insert result: {result}")
                
            except Exception as e:
                logger.error(f"❌ Error inserting event {i+1}: {str(e)}")
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
        logger.info(f"Summary: Inserted {len(events_to_insert)} events, Updated {len(events_to_change)} events, Deleted {len(events_to_delete)} events")
        
        # Return the counts for tracking
        return len(events_to_delete), len(events_to_insert), len(events_to_change)
        
    except Exception as e:
        logger.error(f"Error in update_calendar: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == '__main__':
    main() 