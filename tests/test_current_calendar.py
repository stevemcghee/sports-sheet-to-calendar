#!/usr/bin/env python3
"""
Test script for the new get_current_calendar endpoint
"""

import requests
import json

def test_get_current_calendar():
    """Test the get_current_calendar endpoint"""
    
    # Test data
    test_data = {
        'sheet_name': 'Test Sheet'
    }
    
    try:
        # Make request to the endpoint
        response = requests.post(
            'http://localhost:5000/get_current_calendar',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(test_data)
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Endpoint working correctly!")
                print(f"Calendar name: {data.get('calendar_name')}")
                print(f"Total events: {data.get('total_events')}")
            else:
                print(f"❌ Endpoint returned error: {data.get('error')}")
        else:
            print(f"❌ HTTP error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure app.py is running.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_get_current_calendar() 