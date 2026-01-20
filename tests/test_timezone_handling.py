import unittest
import os
from calendar_sync import parse_sports_events, update_calendar
from unittest.mock import MagicMock

class TestTimezoneHandling(unittest.TestCase):

    def setUp(self):
        # Set the timezone for the test environment to simulate local parsing
        os.environ['TIMEZONE'] = 'America/Los_Angeles' # User's timezone

    def test_update_calendar_with_timezone_change(self):
        """
        Tests that update_calendar correctly identifies an event with a different
        timezone representation as the same event and does not update it if it's equal.
        """
        # Mock the Google Calendar service
        service = MagicMock()

        # This is the event as it exists on Google Calendar, likely stored in UTC ('Z')
        # This time is 11 PM on Sep 6th in Los Angeles
        existing_event = {
            'id': '12345',
            'summary': 'Flag Football 2025 - Game at King City (JV and V)',
            'location': 'King City (JV and V)',
            'description': 'Location: King City (JV and V)\nTime: 11:00 PM',
            'start': {'dateTime': '2025-09-07T06:00:00Z'},
            'end': {'dateTime': '2025-09-07T08:00:00Z'}
        }
        
        # We mock the return of the API call that fetches existing events
        service.events().list().execute.return_value = {'items': [existing_event]}

        # This is the new event data from the spreadsheet. It represents the *same time*
        # as the existing event, but it's specified in local time.
        new_event_data = [
            ['Date', 'Event', 'Location', 'Time'],
            ['09/06/2025', 'Flag Football 2025 - King City at King City (JV and V)', 'King City (JV and V)', '11:00 PM']
        ]
        
        # The parser should read this and create a timezone-aware datetime object
        parsed_events = parse_sports_events(new_event_data, 'Test Sheet')

        # Call the update_calendar function
        deleted, inserted, changed = update_calendar(service, parsed_events, 'test_calendar_id')

        # The event should be identified as the same, so no changes should be made.
        self.assertEqual(deleted, 0, "Event should not be deleted")
        self.assertEqual(inserted, 0, "Event should not be inserted")
        self.assertEqual(changed, 0, "Event should not be changed")

if __name__ == '__main__':
    unittest.main()
