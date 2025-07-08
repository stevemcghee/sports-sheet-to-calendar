#!/usr/bin/env python3
"""
Test script for the new bulk creation functionality.
This script tests the new /apply_all_sheets endpoint.
"""

import requests
import json
import sys

def test_bulk_creation():
    """Test the bulk creation functionality."""
    
    # Test data
    test_data = {
        'spreadsheet_id': '1DiA6HTQjDiPzEua_kxcw175C-uMWGnIq_PAKICbiMzQ',
        'use_traditional_parser': True
    }
    
    print("Testing bulk creation functionality...")
    print(f"Test data: {json.dumps(test_data, indent=2)}")
    
    try:
        # Test the new endpoint
        response = requests.post(
            'http://localhost:5000/apply_all_sheets',
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=300  # 5 minute timeout for bulk operation
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Bulk creation endpoint is working!")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if data.get('success'):
                summary = data.get('summary', {})
                print(f"\n📊 Summary:")
                print(f"  - Total sheets: {summary.get('total_sheets', 0)}")
                print(f"  - Successful sheets: {summary.get('successful_sheets', 0)}")
                print(f"  - Failed sheets: {summary.get('failed_sheets', 0)}")
                print(f"  - Events created: {summary.get('total_events_created', 0)}")
                print(f"  - Events updated: {summary.get('total_events_updated', 0)}")
                print(f"  - Events deleted: {summary.get('total_events_deleted', 0)}")
                
                sheet_results = data.get('sheet_results', {})
                print(f"\n📋 Sheet Results:")
                for sheet_name, result in sheet_results.items():
                    status = "✅ Success" if result.get('success') else "❌ Failed"
                    print(f"  - {sheet_name}: {status}")
                    if result.get('success'):
                        print(f"    Created: {result.get('events_created', 0)}, Updated: {result.get('events_updated', 0)}, Deleted: {result.get('events_deleted', 0)}")
                    else:
                        print(f"    Error: {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ Bulk creation failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure the Flask app is running on http://localhost:5000")
        print("Start the app with: python app.py")
    except requests.exceptions.Timeout:
        print("❌ Request timed out. The bulk operation may be taking longer than expected.")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    test_bulk_creation() 