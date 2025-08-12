import os
import logging
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/calendar'
]

def get_service_account_credentials():
    """Get service account credentials for domain-wide delegation."""
    try:
        # Load service account key from file
        credentials = service_account.Credentials.from_service_account_file(
            'service-account-key.json',
            scopes=SCOPES
        )
        
        # Get the target user email from environment
        target_user = os.getenv('TARGET_USER_EMAIL', 'sloswimtiming@gmail.com')
        
        # Create delegated credentials
        delegated_credentials = credentials.with_subject(target_user)
        
        return delegated_credentials
    except Exception as e:
        logger.error(f"Error creating service account credentials: {e}")
        raise

def get_sheets_service():
    """Get Google Sheets service using service account."""
    try:
        credentials = get_service_account_credentials()
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        logger.error(f"Error creating Sheets service: {e}")
        raise

def get_calendar_service():
    """Get Google Calendar service using service account."""
    try:
        credentials = get_service_account_credentials()
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except Exception as e:
        logger.error(f"Error creating Calendar service: {e}")
        raise

def get_spreadsheet_data(spreadsheet_id):
    """Get data from Google Sheets using service account."""
    try:
        service = get_sheets_service()
        
        # Get all sheets in the spreadsheet
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        sheets_data = {}
        
        for sheet in spreadsheet['sheets']:
            sheet_name = sheet['properties']['title']
            logger.info(f"Processing sheet: {sheet_name}")
            
            # Get data from this sheet
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=sheet_name
            ).execute()
            
            if 'values' in result:
                sheets_data[sheet_name] = result['values']
                logger.info(f"Retrieved {len(result['values'])} rows from {sheet_name}")
            else:
                logger.warning(f"No data found in sheet: {sheet_name}")
                sheets_data[sheet_name] = []
        
        return sheets_data
        
    except HttpError as error:
        logger.error(f"Error accessing spreadsheet: {error}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting spreadsheet data: {e}")
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

    # Handle date ranges like 8/4 - 8/7
    full_range_match_no_year = re.match(r'(\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})', date_str)
    if full_range_match_no_year:
        start_month, start_day, end_month, end_day = map(int, full_range_match_no_year.groups())
        year = datetime.now().year
        start_date = datetime(year, start_month, start_day).date()
        end_date = datetime(year, end_month, end_day).date()
        logger.debug(f"Parsed full date range without year: {start_date} to {end_date}")
        return start_date, end_date

    # Handle date ranges like 8/4 - 8/7/2025
    full_range_match = re.match(r'(\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
    if full_range_match:
        start_month, start_day, end_month, end_day, year = map(int, full_range_match.groups())
        start_date = datetime(year, start_month, start_day).date()
        end_date = datetime(year, end_month, end_day).date()
        logger.debug(f"Parsed full date range: {start_date} to {end_date}")
        return start_date, end_date
    
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

def parse_sports_events(sheet_data, sheet_name):
    """Parse sports events from sheet data."""
    events = []
    
    if not sheet_data or len(sheet_data) < 2:
        logger.warning(f"No data or insufficient data in sheet: {sheet_name}")
        return events
    
    # Assume first row is headers
    headers = sheet_data[0]
    data_rows = sheet_data[1:]
    
    # Find column indices
    date_col = None
    sport_col = None
    event_col = None
    location_col = None
    time_col = None
    
    # Additional column detection for unused columns
    transportation_col = None
    release_col = None
    departure_col = None
    attire_col = None
    notes_col = None
    bus_col = None
    vans_col = None
    
    for i, header in enumerate(headers):
        header_lower = header.lower()
        if 'date' in header_lower:
            date_col = i
        elif 'sport' in header_lower:
            sport_col = i
        elif 'event' in header_lower or 'opponent' in header_lower:
            event_col = i
        elif 'location' in header_lower:
            location_col = i
        elif 'time' in header_lower:
            time_col = i
        elif 'transportation' in header_lower or 'transport' in header_lower or 'bus/vans' in header_lower:
            transportation_col = i
        elif 'release' in header_lower:
            release_col = i
        elif 'departure' in header_lower or 'depart' in header_lower:
            departure_col = i
        elif 'attire' in header_lower or 'uniform' in header_lower:
            attire_col = i
        elif 'notes' in header_lower or 'note' in header_lower:
            notes_col = i
        elif 'bus' in header_lower and 'vans' not in header_lower:
            bus_col = i
        elif 'vans' in header_lower or 'van' in header_lower:
            vans_col = i
    
    if date_col is None:
        logger.warning(f"No date column found in sheet: {sheet_name}")
        return events
    
    for row_idx, row in enumerate(data_rows):
        if len(row) <= date_col:
            continue
            
        try:
            date_str = row[date_col].strip()
            if not date_str:
                continue
                
            # Parse date
            start_date, end_date = parse_date(date_str)
            
            # Get other fields
            sport_name = row[sport_col].strip() if sport_col is not None and len(row) > sport_col else ""
            event_name = row[event_col].strip() if event_col is not None and len(row) > event_col else ""
            location = row[location_col].strip() if location_col is not None and len(row) > location_col else ""
            time_str = row[time_col].strip() if time_col is not None and len(row) > time_col else ""
            
            # Extract additional fields
            transportation = row[transportation_col].strip() if transportation_col is not None and len(row) > transportation_col else ""
            release_time = row[release_col].strip() if release_col is not None and len(row) > release_col else ""
            departure_time = row[departure_col].strip() if departure_col is not None and len(row) > departure_col else ""
            attire = row[attire_col].strip() if attire_col is not None and len(row) > attire_col else ""
            notes = row[notes_col].strip() if notes_col is not None and len(row) > notes_col else ""
            bus = row[bus_col].strip() if bus_col is not None and len(row) > bus_col else ""
            vans = row[vans_col].strip() if vans_col is not None and len(row) > vans_col else ""
            
            # Build description with all available information
            description_parts = [f"Location: {location}"]
            
            if time_str:
                description_parts.append(f"Time: {time_str}")
            
            # Add additional fields to description if they have values
            if transportation and transportation.strip():
                description_parts.append(f"Transportation: {transportation}")
            if release_time and release_time.strip():
                description_parts.append(f"Release Time: {release_time}")
            if departure_time and departure_time.strip():
                description_parts.append(f"Departure Time: {departure_time}")
            if attire and attire.strip():
                description_parts.append(f"Attire: {attire}")
            if notes and notes.strip():
                description_parts.append(f"Notes: {notes}")
            if bus and bus.strip():
                description_parts.append(f"Bus: {bus}")
            if vans and vans.strip():
                description_parts.append(f"Vans: {vans}")
            
            description = "\n".join(description_parts)
            
            # Create event
            event_dict = {
                "summary": f"{sport_name} - {event_name} at {location}",
                "description": description,
                "location": location,
            }

            if end_date:
                event_dict["start"] = {"date": start_date.strftime("%Y-%m-%d")}
                event_dict["end"] = {"date": (end_date + timedelta(days=1)).strftime("%Y-%m-%d")}
            else:
                event_dict["start"] = {"date": start_date.strftime("%Y-%m-%d")}
                event_dict["end"] = {"date": (start_date + timedelta(days=1)).strftime("%Y-%m-%d")}

            
            # Add custom fields for additional data
            if transportation and transportation.strip():
                event_dict["transportation"] = transportation
            if release_time and release_time.strip():
                event_dict["release_time"] = release_time
            if departure_time and departure_time.strip():
                event_dict["departure_time"] = departure_time
            if attire and attire.strip():
                event_dict["attire"] = attire
            if notes and notes.strip():
                event_dict["notes"] = notes
            if bus and bus.strip():
                event_dict["bus"] = bus
            if vans and vans.strip():
                event_dict["vans"] = vans
            
            events.append(event_dict)
            logger.debug(f"Created event: {event_dict['summary']}")
            
        except Exception as e:
            logger.warning(f"Error parsing row {row_idx + 2} in sheet {sheet_name}: {e}")
            continue
    
    return events


def get_calendar_events(calendar_id='primary'):
    """Get existing calendar events using service account."""
    try:
        service = get_calendar_service()
        
        # Get events from the last 30 days to the next 365 days
        now = datetime.utcnow()
        time_min = (now - timedelta(days=30)).isoformat() + 'Z'
        time_max = (now + timedelta(days=365)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        logger.info(f"Retrieved {len(events)} existing calendar events")
        
        return events
        
    except HttpError as error:
        logger.error(f"Error accessing calendar: {error}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting calendar events: {e}")
        raise

def create_calendar_event(event_data, calendar_id='primary'):
    """Create a calendar event using service account."""
    try:
        service = get_calendar_service()
        
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_data
        ).execute()
        
        logger.info(f"Created event: {event.get('summary', 'Unknown')}")
        return event
        
    except HttpError as error:
        logger.error(f"Error creating calendar event: {error}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating calendar event: {e}")
        raise

def update_calendar_event(event_id, event_data, calendar_id='primary'):
    """Update a calendar event using service account."""
    try:
        service = get_calendar_service()
        
        event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_data
        ).execute()
        
        logger.info(f"Updated event: {event.get('summary', 'Unknown')}")
        return event
        
    except HttpError as error:
        logger.error(f"Error updating calendar event: {error}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating calendar event: {e}")
        raise

def delete_calendar_event(event_id, calendar_id='primary'):
    """Delete a calendar event using service account."""
    try:
        service = get_calendar_service()
        
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        logger.info(f"Deleted event with ID: {event_id}")
        
    except HttpError as error:
        logger.error(f"Error deleting calendar event: {error}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting calendar event: {e}")
        raise

def sync_calendar_with_sheets(spreadsheet_id):
    """Main function to sync calendar with sheets data using service account."""
    try:
        logger.info("Starting calendar sync with service account authentication...")
        
        # Get spreadsheet data
        sheets_data = get_spreadsheet_data(spreadsheet_id)
        
        # Parse events from all sheets
        all_events = []
        for sheet_name, sheet_data in sheets_data.items():
            events = parse_sports_events(sheet_data, sheet_name)
            all_events.extend(events)
        
        logger.info(f"Parsed {len(all_events)} events from {len(sheets_data)} sheets")
        
        # Get existing calendar events
        existing_events = get_calendar_events()
        
        # Create lookup dictionaries
        new_events_dict = {event['summary']: event for event in all_events}
        existing_events_dict = {event['summary']: event for event in existing_events}
        
        # Find events to create, update, and delete
        events_to_create = []
        events_to_update = []
        events_to_delete = []
        
        # Find new events
        for summary, event in new_events_dict.items():
            if summary not in existing_events_dict:
                events_to_create.append(event)
        
        # Find events to delete (existing but not in new data)
        for summary, event in existing_events_dict.items():
            if summary not in new_events_dict:
                events_to_delete.append(event)
        
        # Find events to update (both exist but different)
        for summary, new_event in new_events_dict.items():
            if summary in existing_events_dict:
                existing_event = existing_events_dict[summary]
                if new_event != existing_event:
                    new_event['id'] = existing_event['id']  # Need ID for update
                    events_to_update.append(new_event)
        
        # Apply changes
        logger.info(f"Creating {len(events_to_create)} events...")
        for event in events_to_create:
            create_calendar_event(event)
        
        logger.info(f"Updating {len(events_to_update)} events...")
        for event in events_to_update:
            update_calendar_event(event['id'], event)
        
        logger.info(f"Deleting {len(events_to_delete)} events...")
        for event in events_to_delete:
            delete_calendar_event(event['id'])
        
        # Return summary
        return {
            'total_events': len(all_events),
            'events_created': len(events_to_create),
            'events_updated': len(events_to_update),
            'events_deleted': len(events_to_delete),
            'sheets_processed': len(sheets_data)
        }
        
    except Exception as e:
        logger.error(f"Error during calendar sync: {e}")
        raise

if __name__ == "__main__":
    # Test the service account authentication
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    if not spreadsheet_id:
        print("Please set SPREADSHEET_ID environment variable")
        exit(1)
    
    try:
        result = sync_calendar_with_sheets(spreadsheet_id)
        print(f"Sync completed successfully: {result}")
    except Exception as e:
        print(f"Sync failed: {e}")
        exit(1) 