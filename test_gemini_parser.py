import unittest
import os
from unittest.mock import patch, MagicMock
from gemini_parser import parse_sheet_with_gemini, initialize_gemini
from dotenv import load_dotenv

class TestGeminiParser(unittest.TestCase):
    def setUp(self):
        # Sample spreadsheet data
        self.sample_data = [
            ["Event Title", "Date", "Location", "Notes"],
            ["Basketball Game", "2024-04-25 14:00", "Main Gym", "Home game"],
            ["Soccer Practice", "2024-04-26 15:30", "Field 2", "Bring water"],
            ["Track Meet", "2024-04-27 09:00", "City Stadium", "Bus leaves at 8:00"]
        ]

    def test_parse_sheet_with_gemini_success(self):
        # Create mock model
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''
        {
            "events": [
                {
                    "summary": "Basketball Game",
                    "start": {
                        "dateTime": "2024-04-25T14:00:00"
                    },
                    "location": "Main Gym",
                    "notes": "Home game"
                },
                {
                    "summary": "Soccer Practice",
                    "start": {
                        "dateTime": "2024-04-26T15:30:00"
                    },
                    "location": "Field 2",
                    "notes": "Bring water"
                },
                {
                    "summary": "Track Meet",
                    "start": {
                        "dateTime": "2024-04-27T09:00:00"
                    },
                    "location": "City Stadium",
                    "notes": "Bus leaves at 8:00"
                }
            ]
        }
        '''
        mock_model.generate_content.return_value = mock_response

        # Call the function with mock model
        events = parse_sheet_with_gemini(self.sample_data, model=mock_model)

        # Verify the results
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]['summary'], "Basketball Game")
        self.assertEqual(events[0]['start']['dateTime'], "2024-04-25T14:00:00")
        self.assertEqual(events[0]['location'], "Main Gym")
        self.assertEqual(events[0]['notes'], "Home game")

    def test_parse_sheet_with_gemini_empty_data(self):
        # Create mock model
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"events": []}'
        mock_model.generate_content.return_value = mock_response
        
        # Test with empty data
        empty_data = []
        events = parse_sheet_with_gemini(empty_data, model=mock_model)
        self.assertEqual(events, [])

    def test_parse_sheet_with_gemini_invalid_response(self):
        # Create mock model
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Invalid JSON"
        mock_model.generate_content.return_value = mock_response

        # Call the function
        events = parse_sheet_with_gemini(self.sample_data, model=mock_model)
        self.assertEqual(events, [])

    def test_parse_sheet_with_gemini_missing_fields(self):
        # Create mock model
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''
        {
            "events": [
                {
                    "summary": "Basketball Game",
                    "start": {
                        "dateTime": "2024-04-25T14:00:00"
                    }
                }
            ]
        }
        '''
        mock_model.generate_content.return_value = mock_response

        # Call the function
        events = parse_sheet_with_gemini(self.sample_data, model=mock_model)

        # Verify the results
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['summary'], "Basketball Game")
        self.assertEqual(events[0]['start']['dateTime'], "2024-04-25T14:00:00")
        self.assertNotIn('location', events[0])
        self.assertNotIn('notes', events[0])

    @unittest.skipIf(not os.getenv('GEMINI_API_KEY'), "Gemini API key not found")
    def test_parse_sheet_with_real_gemini_api(self):
        """Integration test using the real Gemini API."""
        # Load environment variables
        load_dotenv()
        
        # Simple test data
        test_data = [
            ["Event", "Date", "Location"],
            ["Team Meeting", "2024-05-01 10:00", "Conference Room A"],
            ["Project Review", "2024-05-02 14:30", "Virtual"]
        ]

        try:
            # Initialize real Gemini model
            model = initialize_gemini()
            
            # Call the function with real model
            print("\nTest data sent to Gemini:")
            print(test_data)
            
            print("\nCalling Gemini API...")
            response = model.generate_content(f"""
            Analyze this spreadsheet data and extract calendar events. Each row represents an event.
            Return the events in JSON format with the following structure:
            {{
                "events": [
                    {{
                        "summary": "event title",
                        "start": {{
                            "dateTime": "ISO 8601 datetime string"
                        }},
                        "end": {{
                            "dateTime": "ISO 8601 datetime string"
                        }},
                        "location": "event location"
                    }}
                ]
            }}

            Here's the spreadsheet data:
            {test_data}

            Important:
            - Convert all dates and times to ISO 8601 format
            - Return ONLY the JSON object, no additional text or markdown formatting
            """)
            
            print("\nRaw Gemini Response:")
            print(response.text if hasattr(response, 'text') else str(response))
            
            events = parse_sheet_with_gemini(test_data, model=model)

            # Basic validation of response
            self.assertIsInstance(events, list)
            self.assertTrue(len(events) > 0)
            
            # Verify first event structure
            first_event = events[0]
            self.assertIn('summary', first_event)
            self.assertIn('start', first_event)
            self.assertIn('dateTime', first_event['start'])
            
            # Print parsed events
            print("\nParsed Events:")
            for event in events:
                print(f"\nEvent: {event['summary']}")
                print(f"Date: {event['start']['dateTime']}")
                print(f"Location: {event.get('location', 'N/A')}")

        except Exception as e:
            self.fail(f"Real API test failed: {str(e)}")

    @unittest.skipIf(not os.getenv('GEMINI_API_KEY'), "Gemini API key not found")
    def test_gemini_complex_datetime_formats(self):
        """Test Gemini's ability to parse various complex datetime formats."""
        load_dotenv()
        
        test_data = [
            ["Event", "Date/Time", "Location"],
            ["All Day Event", "2024-05-01", "Room 101"],  # Date only
            ["AM/PM Test", "5/15/24 9:30 AM", "Room 102"],  # AM/PM format
            ["24hr Format", "2024-05-20 14:30", "Room 103"],  # 24-hour format
            ["Date Range", "May 25-27, 2024", "Room 104"],  # Date range
            ["Time Range", "2024-06-01 10:00-12:00", "Room 105"],  # Time range
            ["Multi-Day Time", "Jun 5 2pm - Jun 7 4pm 2024", "Room 106"],  # Multi-day with times
            ["Informal Format", "next Monday 3pm", "Room 107"],  # Relative date
            ["Short Format", "6/1 3:30p", "Room 108"],  # Short format with p for PM
            ["European Format", "01.07.2024 15:45", "Room 109"],  # European date format
            ["ISO-like", "2024-07-15T16:30:00", "Room 110"]  # ISO-like format
        ]

        try:
            model = initialize_gemini()
            print("\nTesting complex datetime formats:")
            print(test_data)
            
            events = parse_sheet_with_gemini(test_data, model=model)
            
            print("\nParsed Events:")
            for event in events:
                print(f"\nEvent: {event['summary']}")
                print(f"Start: {event['start'].get('dateTime', event['start'].get('date', 'N/A'))}")
                if 'end' in event:
                    print(f"End: {event['end'].get('dateTime', event['end'].get('date', 'N/A'))}")
                print(f"Location: {event.get('location', 'N/A')}")
            
            # Verify basic structure
            self.assertIsInstance(events, list)
            self.assertTrue(len(events) > 0)
            
            # Verify each event has required fields
            for event in events:
                self.assertIn('summary', event)
                self.assertIn('start', event)
                self.assertTrue('dateTime' in event['start'] or 'date' in event['start'])
                
        except Exception as e:
            self.fail(f"Complex datetime formats test failed: {str(e)}")

    @unittest.skipIf(not os.getenv('GEMINI_API_KEY'), "Gemini API key not found")
    def test_gemini_timezone_handling(self):
        """Test Gemini's ability to handle timezone specifications."""
        load_dotenv()
        
        test_data = [
            ["Event", "Date/Time", "Location", "Timezone"],
            ["Local Event", "2024-08-01 10:00", "Office", "America/Los_Angeles"],
            ["Remote Event", "2024-08-01 15:00", "Virtual", "Europe/London"],
            ["Pacific Event", "Aug 2 2024 9am PST", "Room 201", ""],
            ["Eastern Event", "8/2/24 5:00 PM EST", "Room 202", ""],
            ["UTC Event", "2024-08-03 13:00 UTC", "Room 203", ""],
            ["GMT Event", "03/08/24 18:00 GMT", "Room 204", ""],
            ["Mixed TZ Event", "Aug 4 2024 3PM PDT / 6PM EDT", "Room 205", ""]
        ]

        try:
            model = initialize_gemini()
            print("\nTesting timezone handling:")
            print(test_data)
            
            events = parse_sheet_with_gemini(test_data, model=model)
            
            print("\nParsed Events:")
            for event in events:
                print(f"\nEvent: {event['summary']}")
                print(f"Start: {event['start'].get('dateTime', 'N/A')}")
                print(f"Timezone: {event['start'].get('timeZone', 'N/A')}")
                print(f"Location: {event.get('location', 'N/A')}")
            
            # Verify basic structure
            self.assertIsInstance(events, list)
            self.assertTrue(len(events) > 0)
            
            # Verify each event has datetime and timezone info
            for event in events:
                self.assertIn('summary', event)
                self.assertIn('start', event)
                self.assertIn('dateTime', event['start'])
                
        except Exception as e:
            self.fail(f"Timezone handling test failed: {str(e)}")

    @unittest.skipIf(not os.getenv('GEMINI_API_KEY'), "Gemini API key not found")
    def test_gemini_recurring_events(self):
        """Test Gemini's ability to handle recurring event specifications."""
        load_dotenv()
        
        test_data = [
            ["Event", "Schedule", "Location"],
            ["Weekly Meeting", "Every Monday 10am", "Room 301"],
            ["Bi-weekly Review", "Every other Wednesday 2pm", "Room 302"],
            ["Monthly Training", "First Thursday of every month 3pm", "Room 303"],
            ["Daily Standup", "Every weekday 9:30am", "Room 304"],
            ["Weekend Event", "Every Sat-Sun 11am-2pm", "Room 305"],
            ["Complex Pattern", "Every Mon/Wed/Fri 8am", "Room 306"],
            ["Limited Series", "Every Tuesday 4pm until Dec 2024", "Room 307"]
        ]

        try:
            model = initialize_gemini()
            print("\nTesting recurring event patterns:")
            print(test_data)
            
            events = parse_sheet_with_gemini(test_data, model=model)
            
            print("\nParsed Events:")
            for event in events:
                print(f"\nEvent: {event['summary']}")
                if 'recurrence' in event:
                    print(f"Recurrence: {event['recurrence']}")
                print(f"Start: {event['start'].get('dateTime', event['start'].get('date', 'N/A'))}")
                print(f"Location: {event.get('location', 'N/A')}")
            
            # Verify basic structure
            self.assertIsInstance(events, list)
            self.assertTrue(len(events) > 0)
            
            # Verify each event has required fields
            for event in events:
                self.assertIn('summary', event)
                self.assertIn('start', event)
                
        except Exception as e:
            self.fail(f"Recurring events test failed: {str(e)}")

if __name__ == '__main__':
    unittest.main() 