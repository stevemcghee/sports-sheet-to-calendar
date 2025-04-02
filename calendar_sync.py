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
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create handlers
scrolling_handler = ScrollingHandler()
file_handler = logging.FileHandler('out.log')

# Create formatters and add it to handlers
# Use shorter time format for console, full format for file
console_formatter = logging.Formatter('%(asctime)s [%(levelname).1s] %(message)s', datefmt='%H:%M:%S')
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

scrolling_handler.setFormatter(console_formatter)
file_handler.setFormatter(file_formatter)

# Add handlers to the logger
logger.addHandler(scrolling_handler)
logger.addHandler(file_handler)

# Prevent logging from propagating to root logger
logger.propagate = False

# Capture all logging
root_logger = logging.getLogger()
root_logger.addHandler(scrolling_handler)
root_logger.addHandler(file_handler)
root_logger.setLevel(logging.DEBUG)

# Prevent other loggers from writing to stdout/stderr
logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
logging.getLogger('google_auth_oauthlib.flow').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/calendar'
]

# Default values from environment variables
DEFAULT_SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
DEFAULT_CALENDAR_NAME = os.getenv('CALENDAR_NAME')
DEFAULT_PROJECT_ID = os.getenv('PROJECT_ID')
DEFAULT_TIMEZONE = os.getenv('TIMEZONE', 'America/Los_Angeles')

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
                creds.refresh(Request())
            else:
                logger.debug("Starting new OAuth flow")
                try:
                    logger.debug("Loading credentials.json")
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    logger.debug("Starting local server for OAuth flow")
                    creds = flow.run_local_server(port=8080)
                    logger.debug("OAuth flow completed successfully")
                except Exception as e:
                    logger.error(f"Error during OAuth flow: {str(e)}")
                    logger.error(f"Error type: {type(e)}")
                    raise
            logger.debug("Saving credentials to token.pickle")
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        logger.debug("Successfully retrieved valid credentials")
        return creds
    except Exception as e:
        logger.error(f"Unexpected error in get_google_credentials: {str(e)}")
        raise

def get_spreadsheet_data(service, spreadsheet_id, sheet_name):
    """Fetch data from Google Sheets."""
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=spreadsheet_id,
        range=f'{sheet_name}!A:I'  # Adjust range to include all relevant columns
    ).execute()
    return result.get('values', [])

def parse_date_range(date_str):
    """Parse a date range string into start and end dates.
    
    Supported formats:
    - Single day: "2/17" or "2/17/2025"
    - Same month range: "2/17-20" or "2/17-20/2025"
    - Cross month range: "2/28-3/2" or "2/28-3/2/2025"
    - Full range with year: "2/17-2/20/2025" or "5/27-5/31/24"
    """
    try:
        # Default year is 2025 for testing
        default_year = 2025
        
        # Split on dash to separate start and end dates
        parts = date_str.split('-')
        
        if len(parts) == 1:
            # Single day format: "2/17" or "2/17/2025"
            start_parts = parts[0].split('/')
            if len(start_parts) == 2:
                month, day = map(int, start_parts)
                year = default_year
            elif len(start_parts) == 3:
                month, day, year = map(int, start_parts)
                if year < 100:
                    year = default_year  # Always use default year for two-digit years
            else:
                return None
                
            try:
                start_date = date(year, month, day)
                end_date = start_date + timedelta(days=1)  # End date is exclusive
                return start_date, end_date
            except ValueError:
                return None
                
        else:
            # Range format
            start_str = parts[0]
            end_str = parts[1]
            year = default_year
            
            # Parse start date
            start_parts = start_str.split('/')
            if len(start_parts) == 2:
                start_month, start_day = map(int, start_parts)
            elif len(start_parts) == 3:
                start_month, start_day, year = map(int, start_parts)
                if year < 100:
                    year = default_year  # Always use default year for two-digit years
            else:
                return None
            
            # Parse end date and year
            end_parts = end_str.split('/')
            
            if len(end_parts) == 3:
                # Format: "2/17-2/20/2025" or "5/27-5/31/24"
                if len(end_parts[2]) == 2:  # Two-digit year
                    year = default_year  # Always use default year for two-digit years
                else:  # Full year
                    year = int(end_parts[2])
                end_parts = end_parts[:2]  # Remove year for further processing
            
            if len(end_parts) == 1:
                # Same month format: "2/17-20"
                try:
                    end_day = int(end_parts[0])
                    end_month = start_month
                except ValueError:
                    return None
            elif len(end_parts) == 2:
                # Cross month format: "2/28-3/2"
                try:
                    end_month, end_day = map(int, end_parts)
                except ValueError:
                    return None
            else:
                return None
            
            try:
                start_date = date(year, start_month, start_day)
                end_date = date(year, end_month, end_day)
                
                # If end date is before start date and it's a cross-month range,
                # it might be a year transition
                if end_date < start_date and end_month < start_month:
                    end_date = date(year + 1, end_month, end_day)
                
                # Add one day to end date to make it exclusive
                end_date = end_date + timedelta(days=1)
                
                # Validate date range is not more than 7 days
                if (end_date - start_date).days > 7:
                    return None
                    
                return start_date, end_date
                
            except ValueError:
                return None
                
    except Exception as e:
        logging.error(f"Error parsing date range: {date_str} - {str(e)}")
        return None

def parse_sports_events(sheet_data, sheet_name):
    """Parse sports events from a sheet."""
    if not sheet_data or len(sheet_data) < 2:
        return []

    # Get sport name from first row or use sheet name
    sport_name = sheet_data[0][0] if sheet_data[0][0] else sheet_name
    events = []

    # Skip header rows
    for row in sheet_data[2:]:
        # Skip rows with insufficient data
        if len(row) < 4 or not row[0] or not row[2]:
            continue

        date_str = row[0]
        event_name = row[2]
        location = row[3] if len(row) > 3 and row[3] else None
        time_str = row[4] if len(row) > 4 and row[4] else None

        # Parse date range
        date_range = parse_date_range(date_str)
        if not date_range:
            logging.error(f"Error parsing date: {date_str}")
            continue

        start_date, end_date = date_range

        # Create event dictionary with base description
        event = {
            'summary': f"{sport_name} - {event_name}" + (f" at {location}" if location else ""),
            'description': f"Sport: {sport_name}\nTime: TBD\nEvent: {event_name}"  # Time always second line
        }

        if location:
            event['description'] += f"\nLocation: {location}"

        # Handle time string if provided
        has_time = False
        if time_str and time_str.strip().lower() not in ['tbd', 'tba', 'all day']:
            try:
                # Try to parse time string
                # First, extract the first time if there are multiple (e.g., "2:00 dive, 3:00 swim")
                time_str = time_str.split(',')[0].split('(')[0].strip()
                
                # Try to match various time formats
                time_match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)?$', time_str)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
                    period = time_match.group(3)

                    # Adjust hour for PM times
                    if period and period.lower() == 'pm' and hour != 12:
                        hour += 12
                    elif period and period.lower() == 'am' and hour == 12:
                        hour = 0
                    elif not period and hour < 8:
                        # If no AM/PM specified and hour is less than 8, assume PM
                        hour += 12

                    # Create datetime objects for start and end
                    start_datetime = datetime.combine(start_date, time(hour, minute))
                    end_datetime = start_datetime + timedelta(hours=2)  # Default 2-hour duration

                    # Set dateTime fields with timezone
                    event['start'] = {'dateTime': start_datetime.strftime('%Y-%m-%dT%H:%M:%S-07:00')}
                    event['end'] = {'dateTime': end_datetime.strftime('%Y-%m-%dT%H:%M:%S-07:00')}
                    has_time = True
                    # Update time in description
                    event['description'] = event['description'].replace('Time: TBD', f'Time: {time_str}')
            except (ValueError, AttributeError) as e:
                logging.error(f"Error parsing time: {time_str} - {str(e)}")
                has_time = False

        # For single day events without time, set a default time of 3:30 PM
        if not has_time and (end_date - start_date).days == 1:
            start_datetime = datetime.combine(start_date, time(15, 30))  # 3:30 PM
            end_datetime = start_datetime + timedelta(hours=2)
            event['start'] = {'dateTime': start_datetime.strftime('%Y-%m-%dT%H:%M:%S-07:00')}
            event['end'] = {'dateTime': end_datetime.strftime('%Y-%m-%dT%H:%M:%S-07:00')}
        elif not has_time:
            # Multi-day event
            event['start'] = {'date': start_date.strftime('%Y-%m-%d')}
            event['end'] = {'date': end_date.strftime('%Y-%m-%d')}

        events.append(event)

    return events

def list_available_sheets(service, spreadsheet_id):
    """List all available sheets in the spreadsheet."""
    try:
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
            'timeZone': DEFAULT_TIMEZONE,
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
                sport_name = events[0]['summary'].split(' - ')[0]
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
    """Update calendar with events efficiently."""
    try:
        # Get existing events
        logger.debug("Fetching existing events")
        existing_events = get_existing_events(service, calendar_id)
        logger.info(f"Found {len(existing_events)} existing events")
        
        # Track events to keep and operation counts
        events_to_keep = set()
        events_deleted = 0
        events_inserted = 0
        events_changed = 0
        
        # Process each new event
        for event in events:
            try:
                key = get_event_key(event)
                events_to_keep.add(key)
                
                if key in existing_events:
                    # Event exists, check if it needs updating
                    existing_event = existing_events[key]
                    if not events_are_equal(event, existing_event):
                        logger.debug(f"Updating existing event: {event['summary']}")
                        service.events().update(
                            calendarId=calendar_id,
                            eventId=existing_event['id'],
                            body=event
                        ).execute()
                        logger.info(f"Updated event: {event['summary']}")
                        events_changed += 1
                else:
                    # Create new event
                    logger.debug(f"Creating new event: {event['summary']}")
                    created_event = service.events().insert(
                        calendarId=calendar_id,
                        body=event
                    ).execute()
                    logger.info(f"Created new event: {event['summary']}")
                    logger.debug(f"Event ID: {created_event.get('id')}")
                    logger.debug(f"Event URL: {created_event.get('htmlLink')}")
                    events_inserted += 1
                    
            except Exception as e:
                logger.error(f"Error processing event {event['summary']}: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                raise
        
        # Delete events that no longer exist
        events_to_delete = set(existing_events.keys()) - events_to_keep
        for key in events_to_delete:
            event = existing_events[key]
            try:
                logger.debug(f"Deleting obsolete event: {event['summary']}")
                service.events().delete(
                    calendarId=calendar_id,
                    eventId=event['id']
                ).execute()
                logger.info(f"Deleted obsolete event: {event['summary']}")
                events_deleted += 1
            except Exception as e:
                logger.error(f"Error deleting event {event['summary']}: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                raise
                
        return events_deleted, events_inserted, events_changed
                
    except Exception as e:
        logger.error(f"Error updating calendar: {str(e)}")
        raise

if __name__ == '__main__':
    main() 