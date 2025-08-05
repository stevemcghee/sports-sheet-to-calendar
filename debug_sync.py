#!/usr/bin/env python3
"""
Debug script to see what's happening during sync
"""

import os
import pickle
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from calendar_sync import (
    get_google_credentials, get_spreadsheet_data, parse_sports_events,
    create_or_get_sports_calendar, update_calendar, get_existing_events
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_single_sheet():
    """Debug a single sheet sync."""
    
    # Get credentials
    creds = get_google_credentials()
    if not creds:
        print("❌ No valid credentials")
        return
    
    # Build services
    sheets_service = build('sheets', 'v4', credentials=creds)
    calendar_service = build('calendar', 'v3', credentials=creds)
    
    # Test with Flag Football sheet
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    sheet_name = "Flag Football"
    
    print(f"🔍 Debugging sheet: {sheet_name}")
    
    # Get sheet data
    data = get_spreadsheet_data(sheets_service, spreadsheet_id, sheet_name)
    print(f"📊 Got {len(data)} rows of data")
    
    # Parse events
    events = parse_sports_events(data, sheet_name)
    print(f"📅 Parsed {len(events)} events")
    
    # Show first event details
    if events:
        first_event = events[0]
        print(f"\n📋 First event details:")
        print(f"  Summary: {first_event.get('summary')}")
        print(f"  Start: {first_event.get('start')}")
        print(f"  End: {first_event.get('end')}")
        print(f"  Description: {first_event.get('description', 'None')}")
    
    # Get calendar
    calendar_name = f"SLOHS {sheet_name}"
    calendar_id = create_or_get_sports_calendar(calendar_service, calendar_name)
    print(f"📅 Calendar ID: {calendar_id}")
    
    # Get existing events
    existing_events = get_existing_events(calendar_service, calendar_id)
    print(f"📅 Found {len(existing_events)} existing events")
    
    # Show first existing event
    if existing_events:
        first_existing = list(existing_events.values())[0]
        print(f"\n📋 First existing event:")
        print(f"  Summary: {first_existing.get('summary')}")
        print(f"  Start: {first_existing.get('start')}")
        print(f"  End: {first_existing.get('end')}")
        print(f"  Description: {first_existing.get('description', 'None')}")
    
    # Run update_calendar with debug info
    print(f"\n🔄 Running update_calendar...")
    deleted, inserted, changed = update_calendar(calendar_service, events, calendar_id)
    print(f"📊 Results: {deleted} deleted, {inserted} inserted, {changed} changed")

if __name__ == "__main__":
    debug_single_sheet() 