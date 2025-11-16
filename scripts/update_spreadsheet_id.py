#!/usr/bin/env python3
"""
Simple script to update the spreadsheet ID in .env file
"""

import os
import re

def update_spreadsheet_id(new_id):
    """Update the spreadsheet ID in .env file."""
    
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        return False
    
    # Read the current .env file
    with open('.env', 'r') as f:
        content = f.read()
    
    # Replace the spreadsheet ID
    pattern = r'SPREADSHEET_ID=.*'
    replacement = f'SPREADSHEET_ID={new_id}'
    
    if re.search(pattern, content):
        new_content = re.sub(pattern, replacement, content)
        
        # Write back to .env
        with open('.env', 'w') as f:
            f.write(new_content)
        
        print(f"✅ Updated SPREADSHEET_ID to: {new_id}")
        return True
    else:
        print("❌ SPREADSHEET_ID not found in .env file")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python update_spreadsheet_id.py <your-spreadsheet-id>")
        print("Example: python update_spreadsheet_id.py 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        sys.exit(1)
    
    spreadsheet_id = sys.argv[1]
    update_spreadsheet_id(spreadsheet_id) 