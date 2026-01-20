#!/usr/bin/env python3

from calendar_sync import parse_sports_events

# Don't set up logging here - use the logger from calendar_sync module

def test_real_data_structure():
    print("=== Testing Real Data Structure ===")
    
    # Simulate the actual data structure from the spreadsheet
    # Based on the logs, this is what the Girls Volleyball data looks like
    test_data = [
        ['Girls Volleyball'],
        ['Date', 'Day', 'Opponent', 'Location', 'Start Time', 'Bus/Vans', 'Release Time', 'Departure Time'],
        ['9/5-9/6', 'Fri, Sat', 'SLO Town Showdown Tournament (V)', 'SLOHS', 'Fri- 1:00, Sat- 9:00', '- ', 'V- 11:00 AM, JV/F- 12:15 PM ', '- '],
        ['9/12-9/13', 'Fri-Sat', 'Clovis North Hard Driven Tournament (V)', 'Clovis North', 'Fri- 2:00, Sat- 8:00 ', 'Vans ', '', '']
    ]
    
    print("Headers:", test_data[1])
    print("Sample row 1:", test_data[2])
    print("Sample row 2:", test_data[3])
    
    # Let's manually check what the column detection should find
    headers = test_data[1]
    for i, header in enumerate(headers):
        header_lower = str(header).lower().strip()
        print(f"Header {i}: '{header}' -> '{header_lower}'")
        if 'release' in header_lower:
            print(f"  -> This should match release_idx = {i}")
        if 'departure' in header_lower:
            print(f"  -> This should match departure_idx = {i}")
        if 'bus/vans' in header_lower:
            print(f"  -> This should match transportation_idx = {i}")
    
    # Let's manually check the data extraction
    print("\n=== Manual Data Extraction Check ===")
    row1 = test_data[2]  # ['9/5-9/6', 'Fri, Sat', 'SLO Town Showdown Tournament (V)', 'SLOHS', 'Fri- 1:00, Sat- 9:00', '- ', 'V- 11:00 AM, JV/F- 12:15 PM ', '- ']
    release_time = row1[6]  # 'V- 11:00 AM, JV/F- 12:15 PM '
    departure_time = row1[7]  # '- '
    
    print(f"Row 1 Release Time: '{release_time}'")
    print(f"Row 1 Departure Time: '{departure_time}'")
    print(f"Release Time stripped: '{release_time.strip()}'")
    print(f"Release Time not in ['-', '--', '- ']: {release_time.strip() not in ['-', '--', '- ']}")
    print(f"Should add Release Time: {release_time and release_time.strip() and release_time.strip() not in ['-', '--', '- ']}")
    
    print("\n=== Running parse_sports_events to see actual column detection ===")
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
    test_real_data_structure() 