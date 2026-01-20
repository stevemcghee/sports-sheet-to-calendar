#!/usr/bin/env python3
"""
Test script to debug event comparison issues
"""

import os
import pickle
from googleapiclient.discovery import build
from calendar_sync import get_existing_events, get_event_key, events_are_equal

def test_event_comparison():
    """Test event comparison logic."""
    
    # Load credentials
    if not os.path.exists('token.pickle'):
        print("❌ No token.pickle found. Please authenticate first.")
        return
    
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    
    # Build calendar service
    service = build('calendar', 'v3', credentials=creds)
    
    # Test with a specific calendar
    calendar_name = "SLOHS Flag Football"
    calendar_id = None
    
    # Find the calendar
    calendar_list = service.calendarList().list().execute()
    for calendar in calendar_list['items']:
        if calendar['summary'] == calendar_name:
            calendar_id = calendar['id']
            break
    
    if not calendar_id:
        print(f"❌ Calendar '{calendar_name}' not found")
        return
    
    print(f"✅ Found calendar: {calendar_name} (ID: {calendar_id})")
    
    # Get existing events
    existing_events = get_existing_events(service, calendar_id)
    print(f"📅 Found {len(existing_events)} existing events")
    
    # Show first few events and their keys
    for i, event in enumerate(list(existing_events.values())[:3]):
        event_key = get_event_key(event)
        print(f"\nEvent {i+1}:")
        print(f"  Summary: {event.get('summary', 'No title')}")
        print(f"  Start: {event.get('start', {})}")
        print(f"  End: {event.get('end', {})}")
        print(f"  Key: {event_key}")
    
    # Test event comparison
    if len(existing_events) >= 2:
        events_list = list(existing_events.values())
        event1 = events_list[0]
        event2 = events_list[1]
        
        print("\n🔍 Comparing events:")
        print(f"Event 1: {event1.get('summary', 'No title')}")
        print(f"Event 2: {event2.get('summary', 'No title')}")
        
        are_equal = events_are_equal(event1, event2)
        print(f"Are equal: {are_equal}")

if __name__ == "__main__":
    test_event_comparison() 