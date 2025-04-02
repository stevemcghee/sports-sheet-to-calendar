import os
from datetime import datetime, timedelta, time
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

def parse_sports_events(sheet_data, sheet_name):
    """Parse sports events from sheet data."""
    events = []
    
    # Get sport name from first row or use sheet name as fallback
    sport_name = None
    if sheet_data and len(sheet_data) > 0 and len(sheet_data[0]) > 0:
        sport_name = sheet_data[0][0].strip()
    if not sport_name:
        sport_name = sheet_name.strip()
        logging.info(f"Using sheet name as sport name: {sport_name}")
    
    logging.info(f"Starting to process events for sport: {sport_name}")
    logging.debug(f"Found sport name: {sport_name}")
    
    # Skip header rows
    for row in sheet_data[2:]:  # Skip first two rows (sport name and headers)
        if not row or len(row) < 4:  # Skip empty rows or rows without enough data
            continue
            
        try:
            # Parse date
            date_str = row[0].strip()
            if not date_str:
                continue
                
            # Handle date ranges
            if '-' in date_str:
                try:
                    # Default year is 2025
                    year = 2025
                    
                    # Check if the year is at the end of the string
                    if '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts) > 1:  # Has at least month/day
                            last_part = parts[-1]
                            if '-' in last_part:  # Year is in the range part
                                try:
                                    year_str = last_part.split('-')[0]
                                    if len(year_str) == 2:  # Two-digit year
                                        year = 2025  # Always use 2025 for two-digit years
                                    else:
                                        year = int(year_str)
                                    # Remove year from date string for further parsing
                                    date_str = '/'.join(parts[:-1]) + '/' + last_part.split('-')[1]
                                except (ValueError, IndexError):
                                    pass  # Not a valid year, keep using default
                            else:  # Year is at the end
                                try:
                                    year_str = last_part
                                    if len(year_str) == 2:  # Two-digit year
                                        year = 2025  # Always use 2025 for two-digit years
                                    else:
                                        year = int(year_str)
                                    # Remove year from date string for further parsing
                                    date_str = '/'.join(parts[:-1])
                                except ValueError:
                                    pass  # Not a valid year, keep using default
                    
                    # Split into start and end parts
                    start_part, end_part = date_str.split('-')
                    start_part = start_part.strip()
                    end_part = end_part.strip()
                    
                    # Parse start date
                    start_parts = start_part.split('/')
                    if len(start_parts) < 2:
                        continue
                    start_month = int(start_parts[0])
                    start_day = int(start_parts[1])
                    
                    # Parse end date
                    if '/' in end_part:  # Has month component
                        end_parts = end_part.split('/')
                        if len(end_parts) >= 2:  # Has month/day
                            end_month = int(end_parts[0])
                            end_day = int(end_parts[1])
                        else:
                            continue
                    else:
                        # Just a day number (e.g., "20" in "2/17-20")
                        end_month = start_month
                        try:
                            end_day = int(end_part)
                        except ValueError:
                            logging.error(f"Invalid end day in range: {date_str}")
                            continue
                    
                    # Validate basic date components
                    if not (1 <= start_month <= 12 and 1 <= start_day <= 31 and
                           1 <= end_month <= 12 and 1 <= end_day <= 31):
                        logging.error(f"Invalid date range components: {date_str}")
                        continue
                    
                    # Create dates and handle year transitions
                    try:
                        start_date = datetime(year, start_month, start_day)
                        end_date = datetime(year, end_month, end_day)
                        
                        # Handle year transitions (e.g., "12/31-1/2")
                        if end_month < start_month:
                            end_date = datetime(year + 1, end_month, end_day)
                        elif end_month == start_month and end_day < start_day:
                            # If end date appears before start date in same month, try next month
                            if end_month < 12:
                                end_date = datetime(year, end_month + 1, end_day)
                            else:
                                end_date = datetime(year + 1, 1, end_day)
                        
                        # Verify the duration is reasonable (allow up to 7 days for tournaments)
                        duration = end_date - start_date
                        if duration.days > 7 or duration.days < 0:
                            logging.warning(f"Invalid date range duration: {date_str}, duration: {duration.days} days. Skipping.")
                            continue
                        
                        # Add one day to end date to make it inclusive
                        end_date = end_date + timedelta(days=1)
                        
                        # Create event
                        event = {
                            'summary': f"{sport_name} - {row[2].strip()} at {row[3].strip()}",
                            'start': {'date': start_date.strftime('%Y-%m-%d')},
                            'end': {'date': end_date.strftime('%Y-%m-%d')},
                            'description': f"Location: {row[3].strip()}\nTime: TBD\nTransportation: {row[5] if len(row) > 5 else '--'}\nRelease Time: {row[6] if len(row) > 6 else '--'}\nDeparture Time: {row[7] if len(row) > 7 else '--'}"
                        }
                        events.append(event)
                        logging.debug(f"Added event: {row[2].strip()} from {start_date.strftime('%Y-%m-%d')} to {(end_date - timedelta(days=1)).strftime('%Y-%m-%d')}")
                        
                    except ValueError as ve:
                        logging.error(f"Invalid date values in range: {date_str} - {str(ve)}")
                        continue
                        
                except Exception as e:
                    logging.error(f"Error parsing date: {date_str}")
                    logging.error(str(e))
                    continue
                    
            # Handle single date
            else:
                try:
                    if '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts) == 2:
                            month = int(parts[0])
                            day = int(parts[1])
                            year = 2025  # Default to 2025
                        elif len(parts) == 3:
                            month = int(parts[0])
                            day = int(parts[1])
                            year_str = parts[2]
                            if len(year_str) == 2:  # Two-digit year
                                year = 2025  # Always use 2025 for two-digit years
                            else:
                                year = int(year_str)
                        else:
                            continue
                    else:
                        continue
                        
                    # Validate date
                    if not (1 <= month <= 12 and 1 <= day <= 31 and 2000 <= year <= 2100):
                        logging.error(f"Invalid date: {date_str}")
                        continue
                        
                    date = datetime(year, month, day)
                    
                    # Parse time
                    time_str = row[4].strip() if len(row) > 4 else ''
                    
                    # Skip time parsing if it's clearly not a time
                    if (not time_str or 
                        time_str.lower() in ['tbd', 'tba', '--', 'all slohs athletes', 'qualifiers', 'all athletes'] or
                        any(loc in time_str.lower() for loc in ['ridge', 'club', 'cc', 'hs', 'gym', 'field', 'pool'])):
                        # Create all-day event
                        event = {
                            'summary': f"{sport_name} - {row[2].strip()} at {row[3].strip()}",
                            'start': {'date': date.strftime('%Y-%m-%d')},
                            'end': {'date': (date + timedelta(days=1)).strftime('%Y-%m-%d')},
                            'description': f"Location: {row[3].strip()}\nTime: TBD\nTransportation: {row[5] if len(row) > 5 else '--'}\nRelease Time: {row[6] if len(row) > 6 else '--'}\nDeparture Time: {row[7] if len(row) > 7 else '--'}"
                        }
                        events.append(event)
                        logging.debug(f"Added all-day event: {row[2].strip()} at {date}")
                        continue
                    
                    try:
                        # Handle special time formats
                        if ',' in time_str:
                            # Take first time if multiple times specified
                            time_str = time_str.split(',')[0].strip()
                            
                        # Clean up time string - remove parenthetical notes and other text
                        time_str = time_str.split('(')[0].strip()  # Remove parenthetical notes
                        time_str = time_str.split('dive')[0].strip()  # Remove 'dive'
                        time_str = time_str.split('swim')[0].strip()  # Remove 'swim'
                        time_str = time_str.split('both')[0].strip()  # Remove 'both'
                        time_str = time_str.split('only')[0].strip()  # Remove 'only'
                        
                        # Add AM/PM if missing
                        if ':' in time_str and not any(x in time_str.upper() for x in ['AM', 'PM']):
                            hour = int(time_str.split(':')[0])
                            if hour < 8:  # Assume PM for early hours
                                time_str += ' PM'
                            elif hour < 12:  # Assume AM for morning hours
                                time_str += ' AM'
                            else:  # Assume PM for afternoon hours
                                time_str += ' PM'
                        elif time_str.replace('.', '').isdigit():  # Handle times like "3" or "4"
                            hour = int(float(time_str))
                            if hour < 8:  # Assume PM for early hours
                                time_str = f"{hour}:00 PM"
                            elif hour < 12:  # Assume AM for morning hours
                                time_str = f"{hour}:00 AM"
                            else:  # Assume PM for afternoon hours
                                time_str = f"{hour}:00 PM"
                        
                        # Parse time
                        try:
                            parsed_time = datetime.strptime(time_str, '%I:%M %p')
                        except ValueError:
                            parsed_time = datetime.strptime(time_str, '%I %p')
                            
                        event_time = datetime.combine(date, parsed_time.time())
                        
                        # Create timed event
                        event = {
                            'summary': f"{sport_name} - {row[2].strip()} at {row[3].strip()}",
                            'start': {'dateTime': event_time.strftime('%Y-%m-%dT%H:%M:%S'), 'timeZone': 'America/Los_Angeles'},
                            'end': {'dateTime': (event_time + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S'), 'timeZone': 'America/Los_Angeles'},
                            'description': f"Location: {row[3].strip()}\nTime: {time_str}\nTransportation: {row[5] if len(row) > 5 else '--'}\nRelease Time: {row[6] if len(row) > 6 else '--'}\nDeparture Time: {row[7] if len(row) > 7 else '--'}"
                        }
                        events.append(event)
                        logging.debug(f"Added timed event: {row[2].strip()} at {event_time}")
                        
                    except Exception as e:
                        logging.error(f"Error processing time: {time_str}")
                        logging.error(str(e))
                        # If time parsing fails, create a timed event with default time (3:30 PM)
                        event_time = datetime.combine(date, time(15, 30))
                        event = {
                            'summary': f"{sport_name} - {row[2].strip()} at {row[3].strip()}",
                            'start': {'dateTime': event_time.strftime('%Y-%m-%dT%H:%M:%S'), 'timeZone': 'America/Los_Angeles'},
                            'end': {'dateTime': (event_time + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S'), 'timeZone': 'America/Los_Angeles'},
                            'description': f"Location: {row[3].strip()}\nTime: TBD\nTransportation: {row[5] if len(row) > 5 else '--'}\nRelease Time: {row[6] if len(row) > 6 else '--'}\nDeparture Time: {row[7] if len(row) > 7 else '--'}"
                        }
                        events.append(event)
                        logging.debug(f"Added timed event after time parsing failed: {row[2].strip()} at {event_time}")
                        continue
                        
                except Exception as e:
                    logging.error(f"Error parsing date: {date_str}")
                    logging.error(str(e))
                    continue
                    
        except Exception as e:
            logging.error(f"Error processing row: {row}")
            logging.error(str(e))
            continue
            
    logging.info(f"Total events found: {len(events)}")
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
            total_events_estimate += len([row for row in data[2:] if row and len(row) >= 4])
            
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
    """Generate a unique key for an event based on its properties."""
    # Extract date and time components
    start = event.get('start', {})
    end = event.get('end', {})
    
    # Get date/time strings, handling both date and dateTime formats
    start_date = start.get('date') or start.get('dateTime', '')
    end_date = end.get('date') or end.get('dateTime', '')
    
    # Get summary and clean it up
    summary = event.get('summary', '').strip()
    
    # Create a normalized key that includes time components
    return f"{start_date}_{end_date}_{summary}"

def events_are_equal(event1, event2):
    """Compare two events to determine if they are equal."""
    # Compare only the fields we care about
    fields_to_compare = ['summary', 'start', 'end', 'description']
    
    for field in fields_to_compare:
        val1 = event1.get(field)
        val2 = event2.get(field)
        
        # Handle None values
        if val1 is None and val2 is None:
            continue
        if val1 is None or val2 is None:
            return False
            
        # Special handling for start/end times
        if field in ['start', 'end']:
            # Compare full dateTime strings, including timezone
            date1 = val1.get('date') or val1.get('dateTime', '')
            date2 = val2.get('date') or val2.get('dateTime', '')
            if date1 != date2:
                return False
        else:
            # For other fields, do exact comparison
            if val1 != val2:
                return False
                
    return True

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