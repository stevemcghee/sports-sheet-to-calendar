#!/usr/bin/env python3
"""
Debug script to see exactly what's happening in update_calendar
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

def debug_update_calendar():
    """Debug the update_calendar logic."""
    
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
    
    print(f"🔍 Debugging update_calendar for: {sheet_name}")
    
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
    
    # Simulate the update_calendar logic
    existing_events_dict = {}
    for event in existing_events.values():
        event_key = get_event_key(event)
        existing_events_dict[event_key] = event
    
    print(f"📋 Created existing_events_dict with {len(existing_events_dict)} events")
    
    # Process each event
    events_to_keep = set()
    events_to_insert = []
    events_to_change = []
    
    print(f"\n🔍 Processing {len(events)} new events:")
    for i, event in enumerate(events):
        event_key = get_event_key(event)
        print(f"\nEvent {i+1}: {event.get('summary', 'Unknown')}")
        print(f"  Key: {event_key}")
        
        if event_key in existing_events_dict:
            print(f"  ✅ Found in existing events")
            existing_event = existing_events_dict[event_key]
            
            if events_are_equal(event, existing_event):
                print(f"  ✅ Events are equal - keeping")
                events_to_keep.add(event_key)
            else:
                print(f"  ⚠️ Events are different - updating")
                events_to_change.append(event)
        else:
            print(f"  ➕ New event - inserting")
            events_to_insert.append(event)
    
    # Find events to delete
    events_to_delete = set()
    for event_key in existing_events_dict:
        if event_key not in events_to_keep:
            print(f"  🗑️ Event to delete: {event_key}")
            events_to_delete.add(event_key)
    
    print(f"\n📊 Summary:")
    print(f"  Events to keep: {len(events_to_keep)}")
    print(f"  Events to insert: {len(events_to_insert)}")
    print(f"  Events to update: {len(events_to_change)}")
    print(f"  Events to delete: {len(events_to_delete)}")
    
    return len(events_to_delete), len(events_to_insert), len(events_to_change)

if __name__ == "__main__":
    deleted, inserted, changed = debug_update_calendar()
    print(f"\n🎯 Final counts: {deleted} deleted, {inserted} inserted, {changed} changed") 