#!/usr/bin/env python3
"""
Debug script to see exactly what's happening with event comparison
"""

import os
import pickle
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import re
from calendar_sync import (
    get_google_credentials, get_spreadsheet_data, parse_sports_events,
    create_or_get_sports_calendar, get_existing_events
)

def get_event_key(event):
    """Generate a unique key for an event based on its start/end times and summary."""
    start = event.get('start', {})
    summary = event.get('summary', '')
    
    # Get start time/date
    if 'dateTime' in start:
        # For datetime events, keep the full datetime string
        start_str = start['dateTime'].split('T')[0]
    elif 'date' in start:
        start_str = start['date']
    else:
        return None
        
    return f"{start_str}_{summary}"

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
    if ('dateTime' in start1 and 'date' in start2) or ('date' in start1 and 'dateTime' in start2):
        date1 = start1.get('date') or start1['dateTime'].split('T')[0]
        date2 = start2.get('date') or start2['dateTime'].split('T')[0]
        if date1 != date2:
            return False
    elif 'dateTime' in start1 and 'dateTime' in start2:
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
    if ('dateTime' in end1 and 'date' in end2) or ('date' in end1 and 'dateTime' in end2):
        date1 = end1.get('date') or end1['dateTime'].split('T')[0]
        date2 = end2.get('date') or end2['dateTime'].split('T')[0]
        if date1 != date2:
            return False
    elif 'dateTime' in end1 and 'dateTime' in end2:
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

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_event_comparison():
    """Debug event comparison logic."""
    
    # Get credentials
    creds = get_google_credentials()
    if not creds:
        print("❌ No valid credentials")
        return
    
    # Build services
    sheets_service = build('sheets', 'v4', credentials=creds)
    calendar_service = build('calendar', 'v3', credentials=creds)
    
    # Test with Football sheet
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    sheet_name = "Football"
    
    print(f"🔍 Debugging sheet: {sheet_name}")
    
    # Get sheet data and parse events
    data = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
    events = parse_sports_events(data, sheet_name)
    print(f"📅 Parsed {len(events)} events")
    
    # Get calendar
    calendar_name = f"SLOHS {sheet_name}"
    calendar_id = create_or_get_sports_calendar(calendar_service, calendar_name)
    
    # Get existing events
    existing_events = get_existing_events(calendar_service, calendar_id)
    print(f"📅 Found {len(existing_events)} existing events")
    
    # Compare first few events
    print(f"\n🔍 Comparing events:")
    for i, new_event in enumerate(events[:3]):
        print(f"\nNew Event {i+1}:")
        print(f"  Summary: {new_event.get('summary')}")
        print(f"  Start: {new_event.get('start')}")
        print(f"  End: {new_event.get('end')}")
        print(f"  Description: {new_event.get('description', 'None')}")
        
        new_key = get_event_key(new_event)
        print(f"  Key: {new_key}")
        
        # Find matching existing event
        found_match = False
        for existing_key, existing_event in existing_events.items():
            if new_key == existing_key:
                print(f"  ✅ Found matching existing event!")
                print(f"  Existing Summary: {existing_event.get('summary')}")
                print(f"  Existing Start: {existing_event.get('start')}")
                print(f"  Existing End: {existing_event.get('end')}")
                print(f"  Existing Description: {existing_event.get('description', 'None')}")
                
                # Test equality
                are_equal = events_are_equal(new_event, existing_event)
                print(f"  Events are equal: {are_equal}")
                found_match = True
                break
        
        if not found_match:
            print(f"  ❌ No matching existing event found")
            print(f"  Available existing keys:")
            for j, (existing_key, existing_event) in enumerate(list(existing_events.items())[:3]):
                print(f"    {j+1}. {existing_key}")
                print(f"       Summary: {existing_event.get('summary')}")

if __name__ == "__main__":
    debug_event_comparison()