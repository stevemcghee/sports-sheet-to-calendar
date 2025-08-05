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
from calendar_sync import (
    get_google_credentials, get_spreadsheet_data, parse_sports_events,
    create_or_get_sports_calendar, get_existing_events, get_event_key, events_are_equal
)

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