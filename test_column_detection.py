#!/usr/bin/env python3

import logging
from calendar_sync import parse_sports_events

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_column_detection():
    print("=== Testing Column Detection ===")
    
    # Test 1: With vans data
    print("\nTest 1: With vans data")
    test_data1 = [
        ['Cross Country'],
        ['Date', 'Day', 'Opponent', 'Location', 'Start Time', 'Bus/Vans', 'Release Time', 'Departure Time'],
        ['9/12/2025', 'Fri-Sat', 'Clovis North Hard Driven Tournament (V)', 'Clovis North', 'Fri- 2:00, Sat- 8:00 ', 'Vans ', '', '']
    ]
    events1 = parse_sports_events(test_data1, 'Cross Country')
    print(f"Events created: {len(events1)}")
    if events1:
        print(f"Description: {repr(events1[0]['description'])}")
    
    # Test 2: With empty vans data
    print("\nTest 2: With empty vans data")
    test_data2 = [
        ['Cross Country'],
        ['Date', 'Day', 'Opponent', 'Location', 'Start Time', 'Bus/Vans', 'Release Time', 'Departure Time'],
        ['9/12/2025', 'Fri-Sat', 'Clovis North Hard Driven Tournament (V)', 'Clovis North', 'Fri- 2:00, Sat- 8:00 ', '- ', '', '']
    ]
    events2 = parse_sports_events(test_data2, 'Cross Country')
    print(f"Events created: {len(events2)}")
    if events2:
        print(f"Description: {repr(events2[0]['description'])}")
    
    # Test 3: With vans data that has content
    print("\nTest 3: With vans data that has content")
    test_data3 = [
        ['Cross Country'],
        ['Date', 'Day', 'Opponent', 'Location', 'Start Time', 'Bus/Vans', 'Release Time', 'Departure Time'],
        ['9/12/2025', 'Fri-Sat', 'Clovis North Hard Driven Tournament (V)', 'Clovis North', 'Fri- 2:00, Sat- 8:00 ', 'Vans (Need Drivers)', '', '']
    ]
    events3 = parse_sports_events(test_data3, 'Cross Country')
    print(f"Events created: {len(events3)}")
    if events3:
        print(f"Description: {repr(events3[0]['description'])}")

if __name__ == "__main__":
    test_column_detection() 