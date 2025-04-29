import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Load environment variables
load_dotenv()

def initialize_gemini():
    """Initialize the Gemini API with the API key."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')

def parse_sheet_with_gemini(values, model=None):
    """Parse sheet contents using Gemini.
    
    Args:
        values (list): List of rows from the spreadsheet
        model (GenerativeModel, optional): Pre-configured Gemini model for testing
        
    Returns:
        list: List of parsed calendar events
    """
    try:
        # Use provided model or initialize a new one
        gemini_model = model or initialize_gemini()
        
        prompt = f"""
        Analyze this spreadsheet data and extract calendar events. Each row represents an event.
        Return the events in JSON format with the following structure:
        {{
            "events": [
                {{
                    "summary": "event title",
                    "start": {{
                        "dateTime": "ISO 8601 datetime string",
                        "timeZone": "IANA timezone name (e.g., America/Los_Angeles)"
                    }},
                    "end": {{
                        "dateTime": "ISO 8601 datetime string",
                        "timeZone": "IANA timezone name (e.g., America/Los_Angeles)"
                    }},
                    "location": "event location",
                    "description": "event description",
                    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO;UNTIL=20241231T235959Z"],  # For recurring events
                    "transportation": "transportation details",
                    "release_time": "release time",
                    "departure_time": "departure time",
                    "attire": "dress code",
                    "notes": "additional notes"
                }}
            ]
        }}

        Here's the spreadsheet data:
        {values}

        Important:
        - Convert all dates and times to ISO 8601 format
        - If a time is not specified, assume 9:00 AM
        - If a date is not specified, use today's date
        - For end times, if not specified, assume 1 hour after start time
        - Use "N/A" for any empty or missing fields
        - Preserve all original text exactly as it appears in the spreadsheet
        - If a field contains multiple values (like multiple locations), combine them with semicolons
        - For transportation, include any bus numbers, departure points, or special instructions
        - For attire, include any specific dress code requirements
        - For notes, include any additional information that doesn't fit in other fields
        - Return only valid events with at least a title and date
        - Maintain the original order of events as they appear in the spreadsheet
        - Return ONLY the JSON object, no additional text or markdown formatting
        - Escape any special characters in strings (e.g., quotes, newlines)
        - Do not include any comments or explanations in the JSON
        - If you can't parse an event, skip it and continue with the next one
        - Return an empty events list if no valid events are found

        For recurring events:
        - Use RRULE format for recurrence rules
        - Common patterns:
          * Weekly: RRULE:FREQ=WEEKLY;BYDAY=MO (every Monday)
          * Bi-weekly: RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=WE (every other Wednesday)
          * Monthly: RRULE:FREQ=MONTHLY;BYDAY=1TH (first Thursday of month)
          * Daily: RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR (weekdays)
          * Multiple days: RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR (Mon/Wed/Fri)
          * Until date: RRULE:FREQ=WEEKLY;BYDAY=TU;UNTIL=20241231T235959Z (until end of 2024)

        For timezones:
        - Always include the timeZone field
        - Use IANA timezone names (e.g., America/Los_Angeles, Europe/London)
        - For timezone abbreviations (PST, EST, etc.), convert to full IANA names
        - For mixed timezone events, use the primary timezone
        - Default to America/Los_Angeles if no timezone is specified
        """

        response = gemini_model.generate_content(prompt)
        
        # Get the response text
        response_text = response.text if hasattr(response, 'text') else str(response)
        print(f"Raw Gemini response: {response_text}")  # Debug logging
        
        # Try to find JSON content in the response
        try:
            # Look for JSON content between ```json and ``` markers
            if '```json' in response_text:
                json_str = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                json_str = response_text.split('```')[1].split('```')[0].strip()
            else:
                json_str = response_text.strip()
            
            print(f"Extracted JSON string: {json_str}")  # Debug logging
            
            # Clean up the JSON string
            json_str = json_str.replace('\n', ' ').replace('\r', '')
            
            # Try to parse the JSON
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"Initial JSON parse failed: {e}")  # Debug logging
                # If parsing fails, try to fix common issues
                json_str = json_str.replace('\\"', '"')  # Fix escaped quotes
                json_str = json_str.replace('\\n', ' ')  # Replace newlines with spaces
                json_str = json_str.replace('\\t', ' ')  # Replace tabs with spaces
                json_str = json_str.replace('\\r', ' ')  # Replace carriage returns with spaces
                json_str = re.sub(r'(?<!\\)"', r'\"', json_str)  # Escape unescaped quotes
                json_str = re.sub(r'\\{2,}', r'\\', json_str)  # Fix multiple backslashes
                
                print(f"Cleaned JSON string: {json_str}")  # Debug logging
                
                # Try parsing again
                result = json.loads(json_str)
            
            # Validate the result structure
            if not isinstance(result, dict):
                print(f"Result is not a dictionary: {result}")
                return []
                
            if 'events' not in result:
                print(f"No 'events' key in result: {result}")
                return []
                
            events = result.get('events', [])
            if not isinstance(events, list):
                print(f"Events is not a list: {events}")
                return []
                
            print(f"Successfully parsed {len(events)} events")  # Debug logging
            return events
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from Gemini response: {e}")
            print(f"Response text: {response_text}")
            return []
            
    except Exception as e:
        print(f"Error parsing with Gemini: {e}")
        return [] 