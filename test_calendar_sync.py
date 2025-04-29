# All date ranges in these tests are INCLUSIVE
# For example:
# - A range of "2/15-17/2025" means the event spans from Feb 15 through Feb 17 (inclusive)
# - A single day event like "2/15/2025" spans that entire day
# - A range like "4/30-5/2" spans from April 30 through May 2 (inclusive)

import unittest
from datetime import datetime, timedelta
from calendar_sync import (
    parse_sports_events, create_or_get_sports_calendar, delete_all_events,
    update_calendar, get_event_key, get_existing_events, events_are_equal
)
from unittest.mock import MagicMock, patch, call
import logging
import os

class TestCalendarSync(unittest.TestCase):
    def test_parse_sports_events(self):
        # Test data
        test_data = [
            ["Basketball"],  # Sport name row
            ["Date", "Day", "Event", "Location", "Time", "Transportation", "Release", "Departure"],  # Headers
            ["2/10/2025", "Mon", "Team A", "Home", "3:00 PM", "", "", ""],
            ["2/15-17/2025", "Fri-Sun", "Team B", "Away", "TBD", "", "", ""],  # Inclusive: Feb 15-17
            ["2/20/2025", "Wed", "Team C", "Home", "5:00 PM", "", "", ""],
        ]

        # Parse events
        events = parse_sports_events(test_data, "Basketball")

        # Assertions
        self.assertEqual(len(events), 3)

        # Test first event
        self.assertEqual(events[0]['summary'], 'Basketball - Team A at Home')
        self.assertEqual(events[0]['start']['dateTime'], "2025-02-10T15:00:00")
        self.assertEqual(events[0]['end']['dateTime'], "2025-02-10T17:00:00")

        # Test date range event (inclusive range)
        self.assertEqual(events[1]['summary'], 'Basketball - Team B at Away')
        self.assertEqual(events[1]['start']['dateTime'], "2025-02-15T00:00:00")
        self.assertEqual(events[1]['end']['dateTime'], "2025-02-17T00:00:00")

        # Test event with minimal information
        self.assertEqual(events[2]['summary'], 'Basketball - Team C at Home')
        self.assertEqual(events[2]['start']['dateTime'], "2025-02-20T17:00:00")
        self.assertEqual(events[2]['end']['dateTime'], "2025-02-20T19:00:00")

    def test_parse_sports_events_empty_data(self):
        events = parse_sports_events([], "Empty Sheet")
        self.assertEqual(len(events), 0)

    def test_parse_sports_events_invalid_data(self):
        test_data = [
            ["Basketball"],  # Sport name row
            ["Date", "Day", "Event", "Location", "Time"],  # Headers
            ["invalid_date", "Mon", "Team A", "Home", "3:00 PM"],  # Invalid date
        ]
        events = parse_sports_events(test_data, "Basketball")
        self.assertEqual(len(events), 0)

    def test_parse_sports_events_basic(self):
        test_data = [
            ["Basketball"],
            ["Date", "Day", "Event", "Location", "Time"],
            ["4/15/2025", "Mon", "Team A", "Home", "3:00 PM"],
            ["4/16-18/2025", "Tue-Thu", "Team B", "Away", "All Day"],  # Inclusive: Apr 16-18
        ]
        
        events = parse_sports_events(test_data, "Basketball")
        self.assertEqual(len(events), 2)
        
        # Check first event (timed)
        self.assertEqual(events[0]['summary'], 'Basketball - Team A at Home')
        self.assertEqual(events[0]['start']['dateTime'], "2025-04-15T15:00:00")
        self.assertEqual(events[0]['end']['dateTime'], "2025-04-15T17:00:00")
        
        # Check second event (all-day, inclusive range)
        self.assertEqual(events[1]['summary'], 'Basketball - Team B at Away')
        self.assertEqual(events[1]['start']['dateTime'], "2025-04-16T00:00:00")
        self.assertEqual(events[1]['end']['dateTime'], "2025-04-18T00:00:00")

    def test_parse_sports_events_date_ranges(self):
        test_data = [
            ["Track"],
            ["Date", "Day", "Event", "Location", "Time"],
            ["2/10-13/2025", "Mon-Thu", "TRYOUTS", "SLOHS", "All SLOHS Athletes"],  # Inclusive: Feb 10-13
            ["4/4-5/2025", "Fri-Sat", "Tournament", "SLOHS", "Qualifiers"],  # Inclusive: Apr 4-5
            ["5/7-10/2025", "Wed-Sat", "CIF", "TBD", "all athletes"],  # Inclusive: May 7-10
        ]
        
        events = parse_sports_events(test_data, "Track")
        self.assertEqual(len(events), 3)
        
        # Check first event (inclusive range)
        self.assertEqual(events[0]['start']['dateTime'], "2025-02-10T00:00:00")
        self.assertEqual(events[0]['end']['dateTime'], "2025-02-13T00:00:00")
        
        # Check second event (inclusive range)
        self.assertEqual(events[1]['start']['dateTime'], "2025-04-04T00:00:00")
        self.assertEqual(events[1]['end']['dateTime'], "2025-04-05T00:00:00")
        
        # Check third event (inclusive range)
        self.assertEqual(events[2]['start']['dateTime'], "2025-05-07T00:00:00")
        self.assertEqual(events[2]['end']['dateTime'], "2025-05-10T00:00:00")

    def test_parse_sports_events_special_times(self):
        test_data = [
            ["Golf"],
            ["Date", "Day", "Event", "Location", "Time"],
            ["4/15/2025", "Mon", "Match", "Home", "2:00 dive, 3:00 swim"],
            ["4/16/2025", "Tue", "Match", "Away", "3 PM"],
            ["4/17/2025", "Wed", "Match", "Home", "4"],
        ]
        
        events = parse_sports_events(test_data, "Golf")
        self.assertEqual(len(events), 3)
        
        # Check swim and dive time
        self.assertEqual(events[0]['start']['dateTime'], "2025-04-15T14:00:00")
        self.assertEqual(events[0]['end']['dateTime'], "2025-04-15T17:00:00")
        
        # Check PM time
        self.assertEqual(events[1]['start']['dateTime'], "2025-04-16T15:00:00")
        self.assertEqual(events[1]['end']['dateTime'], "2025-04-16T17:00:00")
        
        # Check implied PM time
        self.assertEqual(events[2]['start']['dateTime'], "2025-04-17T16:00:00")
        self.assertEqual(events[2]['end']['dateTime'], "2025-04-17T18:00:00")

    def test_parse_sports_events_special_dates(self):
        # Test data with special date formats
        test_data = [
            ["Boys Golf 2025"],  # Sport name row
            ["Date", "Day", "Event", "Location", "Time", "Transportation", "Release", "Departure"],  # Headers
            ["week of 4/28/2025", "Mon", "Match", "SLOHS", "3:30", "", "", ""],
            ["5/12 or 5/13/2025", "Mon", "Match", "TBD", "TBD", "", "", ""],  # Invalid format
        ]
        
        events = parse_sports_events(test_data, "Golf")
        self.assertEqual(len(events), 0)  # Both dates are invalid formats

    def test_parse_sports_events_locations_as_times(self):
        # Test data with proper time values
        test_data = [
            ["Boys Golf 2025"],  # Sport name row
            ["Date", "Day", "Event", "Location", "Time", "Transportation", "Release", "Departure"],  # Headers
            ["3/1/2025", "Mon", "Match", "SLOHS", "3:00 PM", "", "", ""],
            ["3/2/2025", "Tue", "Match", "AGHS", "4:00 PM", "", "", ""],
            ["3/3/2025", "Wed", "Match", "PRHS", "5:00 PM", "", "", ""],
        ]
        
        events = parse_sports_events(test_data, "Golf")
        self.assertEqual(len(events), 3)
        
        # All events should use dateTime
        for i, event in enumerate(events, start=1):
            self.assertTrue('dateTime' in event['start'])
            self.assertEqual(event['start']['dateTime'], f"2025-03-{i}T15:00:00")
            self.assertEqual(event['end']['dateTime'], f"2025-03-{i}T17:00:00")

    def test_parse_sports_events_empty_sport_name(self):
        """Test that sheet name is used when sport name is empty."""
        test_data = [
            [""],  # Empty sport name
            ["Date", "Day", "Event", "Location", "Time", "Transportation", "Release", "Departure"],
            ["2/10/2025", "Mon", "Team A", "Home", "3:00 PM", "", "", ""],
        ]
        
        events = parse_sports_events(test_data, "Basketball")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['summary'], 'Basketball - Team A at Home')

if __name__ == '__main__':
    unittest.main() 