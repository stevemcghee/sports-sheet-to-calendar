#!/usr/bin/env python3

import logging
from calendar_sync import parse_sports_events

# Set up logging to see ALL logs
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

def test_column_detection_debug():
    print("=== Testing Column Detection with Debug Logging ===")
    
    test_data = [
        ['Girls Volleyball'],
        ['Date', 'Day', 'Opponent', 'Location', 'Start Time', 'Bus/Vans', 'Release Time', 'Departure Time'],
        ['9/5-9/6', 'Fri, Sat', 'SLO Town Showdown Tournament (V)', 'SLOHS', 'Fri- 1:00, Sat- 9:00', '- ', 'V- 11:00 AM, JV/F- 12:15 PM ', '- ']
    ]
    
    print("Running parse_sports_events...")
    events = parse_sports_events(test_data, 'Girls Volleyball')
    
    print(f"\nEvents created: {len(events)}")
    for i, event in enumerate(events):
        print(f"\nEvent {i+1}:")
        print(f"  Summary: {event.get('summary', 'No summary')}")
        print(f"  Description: {repr(event.get('description', 'No description'))}")
        print("  Custom fields:")
        for field in ['transportation', 'release_time', 'departure_time', 'attire', 'notes', 'bus', 'vans']:
            value = event.get(field)
            if value:
                print(f"    {field}: {repr(value)}")

if __name__ == "__main__":
    test_column_detection_debug() 