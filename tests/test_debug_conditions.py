#!/usr/bin/env python3

def test_column_detection_conditions():
    print("=== Testing Column Detection Conditions ===")
    
    headers = ['Date', 'Day', 'Opponent', 'Location', 'Start Time', 'Bus/Vans', 'Release Time', 'Departure Time']
    
    for i, header in enumerate(headers):
        header_lower = str(header).lower().strip()
        print(f"\nHeader {i}: '{header}' -> '{header_lower}'")
        
        # Test each condition
        if 'date' in header_lower:
            print(f"  ✓ Matches 'date' -> date_idx = {i}")
        if 'event' in header_lower or 'title' in header_lower or 'name' in header_lower or 'opponent' in header_lower:
            print(f"  ✓ Matches 'event' -> event_idx = {i}")
        if 'location' in header_lower or 'place' in header_lower or 'venue' in header_lower:
            print(f"  ✓ Matches 'location' -> location_idx = {i}")
        if 'time' in header_lower:
            print(f"  ✓ Matches 'time' -> time_idx = {i}")
        if 'transportation' in header_lower or 'transport' in header_lower or 'bus/vans' in header_lower:
            print(f"  ✓ Matches 'transportation' -> transportation_idx = {i}")
        if 'release' in header_lower:
            print(f"  ✓ Matches 'release' -> release_idx = {i}")
        if 'departure' in header_lower or 'depart' in header_lower:
            print(f"  ✓ Matches 'departure' -> departure_idx = {i}")
        if 'attire' in header_lower or 'uniform' in header_lower:
            print(f"  ✓ Matches 'attire' -> attire_idx = {i}")
        if 'notes' in header_lower or 'note' in header_lower:
            print(f"  ✓ Matches 'notes' -> notes_idx = {i}")
        if 'bus' in header_lower and 'vans' in header_lower:
            print(f"  ✓ Matches 'bus' AND 'vans' -> transportation_idx = {i}")
        if 'bus' in header_lower:
            print(f"  ✓ Matches 'bus' -> bus_idx = {i}")
        if 'vans' in header_lower or 'van' in header_lower:
            print(f"  ✓ Matches 'vans' -> vans_idx = {i}")

if __name__ == "__main__":
    test_column_detection_conditions() 