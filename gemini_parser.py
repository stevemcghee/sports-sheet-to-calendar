import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
import re
import datetime

# Load environment variables
load_dotenv()

def initialize_gemini():
    """Initialize the Gemini API with the API key."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    genai.configure(api_key=api_key)

    # Configure safety settings
    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE",
        },
    ]

    return genai.GenerativeModel('models/gemini-1.5-pro-latest', safety_settings=safety_settings)

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
        
        For timed events (with specific time):
        {{
            "events": [
                {{
                    "summary": "Sport Name: Event Name @ Location",
                    "start": {{
                        "dateTime": "YYYY-MM-DDTHH:MM:SS",
                        "timeZone": "America/Los_Angeles"
                    }},
                    "end": {{
                        "dateTime": "YYYY-MM-DDTHH:MM:SS",
                        "timeZone": "America/Los_Angeles"
                    }},
                    "location": "event location",
                    "description": "Location: location"
                }}
            ]
        }}
        
        For all-day events (no specific time):
        {{
            "events": [
                {{
                    "summary": "Sport Name: Event Name @ Location",
                    "start": {{
                        "date": "YYYY-MM-DD"
                    }},
                    "end": {{
                        "date": "YYYY-MM-DD"
                    }},
                    "location": "event location",
                    "description": "Location: location"
                }}
            ]
        }}

        Here's the spreadsheet data:
        {values}

        Important:
        1. Format Requirements:
           - First row contains the sport name
           - Second row contains column headers
           - Subsequent rows contain event data
           - Required columns: "Start Datetime", "Event", "Location"
           - Optional columns: "End Datetime", "Recurrence"

        2. Event Formatting:
           - Summary format: "{{sport_name}}: {{event_name}} @ {{location}}"
           - Description format: "Location: {{location}}"
           - All events must have a start datetime
           - If end datetime is not provided, add 2 hours to start time
           - Use America/Los_Angeles timezone for all events

        3. Datetime Handling:
           - Accept these datetime formats:
             * YYYY-MM-DD HH:MM
             * MM/DD/YYYY HH:MM
             * Relative dates (e.g., "next Monday", "every Tuesday")
             * Recurring patterns (e.g., "every Monday", "every other Wednesday")
           - For events WITH time: Convert to ISO 8601 format (YYYY-MM-DDTHH:MM:SS) and use dateTime format
           - For events WITHOUT time: Use date format (YYYY-MM-DD) for all-day events
           - If time is missing, create an all-day event using date format
           - If date is missing, skip the event

        4. Recurring Events:
           - If an event is recurring, include a recurrence rule in RRULE format
           - Common patterns:
             * Weekly: "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"
             * Bi-weekly: "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=WE"
             * Monthly: "RRULE:FREQ=MONTHLY;BYDAY=1TH"
             * Daily: "RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR"
           - Include end date if specified (e.g., "until Dec 2024")
           - Skip if recurrence pattern is unclear

        5. Data Processing:
           - Skip any rows that don't have all required fields
           - Preserve original text exactly as it appears
           - Return only valid events with all required fields
           - Maintain the original order of events
           - Return ONLY the JSON object, no additional text
           - Escape special characters in strings
           - Skip any events that can't be properly parsed

        6. Error Handling:
           - If no valid events are found, return empty events list
           - Log any parsing errors but continue processing
           - Skip events with invalid datetime formats
           - Skip events missing required fields

        Return ONLY the JSON object, no additional text or markdown formatting.
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
                
            # Validate and clean each event
            cleaned_events = []
            for event in events:
                try:
                    # Ensure required fields are present
                    if not all(key in event for key in ['summary', 'start', 'end', 'location', 'description']):
                        print(f"Missing required fields in event: {event}")
                        continue
                        
                    # Determine if this is an all-day event or timed event
                    is_all_day = 'date' in event['start'] and 'date' in event['end']
                    is_timed = 'dateTime' in event['start'] and 'dateTime' in event['end']
                    
                    if not (is_all_day or is_timed):
                        print(f"Event must have either date (all-day) or dateTime (timed) format: {event}")
                        continue
                    
                    if is_all_day:
                        # All-day event
                        cleaned_event = {
                            'summary': event['summary'].strip(),
                            'start': {
                                'date': event['start']['date'].strip()
                            },
                            'end': {
                                'date': event['end']['date'].strip()
                            },
                            'location': event['location'].strip(),
                            'description': event['description'].strip()
                        }
                        
                        # Validate date format (YYYY-MM-DD)
                        try:
                            datetime.datetime.strptime(cleaned_event['start']['date'], '%Y-%m-%d')
                            datetime.datetime.strptime(cleaned_event['end']['date'], '%Y-%m-%d')
                        except ValueError:
                            print(f"Invalid date format in all-day event: {cleaned_event}")
                            continue
                    else:
                        # Timed event
                        cleaned_event = {
                            'summary': event['summary'].strip(),
                            'start': {
                                'dateTime': event['start']['dateTime'].strip(),
                                'timeZone': 'America/Los_Angeles'
                            },
                            'end': {
                                'dateTime': event['end']['dateTime'].strip(),
                                'timeZone': 'America/Los_Angeles'
                            },
                            'location': event['location'].strip(),
                            'description': event['description'].strip()
                        }
                        
                        # Validate datetime format
                        try:
                            datetime.datetime.fromisoformat(cleaned_event['start']['dateTime'].replace('Z', '+00:00'))
                            datetime.datetime.fromisoformat(cleaned_event['end']['dateTime'].replace('Z', '+00:00'))
                        except ValueError:
                            print(f"Invalid datetime format in timed event: {cleaned_event}")
                            continue

                    # Validate recurrence rule if present
                    if 'recurrence' in event:
                        if not isinstance(event['recurrence'], list):
                            print(f"Invalid recurrence format in event: {event}")
                            continue
                        for rule in event['recurrence']:
                            if not rule.startswith('RRULE:'):
                                print(f"Invalid recurrence rule format: {rule}")
                                continue
                        cleaned_event['recurrence'] = event['recurrence']
                        
                    cleaned_events.append(cleaned_event)
                except Exception as e:
                    print(f"Error cleaning event: {e}")
                    continue
                    
            print(f"Successfully parsed {len(cleaned_events)} events")  # Debug logging
            return cleaned_events
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from Gemini response: {e}")
            print(f"Response text: {response_text}")
            return []
            
    except Exception as e:
        print(f"Error parsing with Gemini: {e}")
        return [] 