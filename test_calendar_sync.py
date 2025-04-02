import unittest
from datetime import datetime, timedelta
from calendar_sync import (
    parse_sports_events, create_or_get_sports_calendar, delete_all_events,
    update_calendar, get_event_key, get_existing_events, events_are_equal
)
from unittest.mock import MagicMock, patch, call
import logging

class TestCalendarSync(unittest.TestCase):
    def test_parse_sports_events(self):
        # Test data
        test_data = [
            ["Basketball"],  # Sport name row
            ["Date", "Day", "Event", "Location", "Time", "Transportation", "Release", "Departure"],  # Headers
            ["2/10/2024", "Mon", "Team A", "Home", "3:00 PM", "", "", ""],
            ["2/15-17/2024", "Fri-Sun", "Team B", "Away", "TBD", "", "", ""],
            ["2/20/2024", "Wed", "Team C", "Home", "5:00 PM", "", "", ""],
        ]

        # Parse events
        events = parse_sports_events(test_data, "Basketball")

        # Assertions
        self.assertEqual(len(events), 3)

        # Test first event
        self.assertEqual(events[0]['summary'], 'Basketball - Team A at Home')
        self.assertEqual(events[0]['start']['dateTime'], "2024-02-10T15:00:00")

        # Test date range event
        self.assertEqual(events[1]['summary'], 'Basketball - Team B at Away')
        self.assertEqual(events[1]['start']['date'], "2024-02-15")
        self.assertEqual(events[1]['end']['date'], "2024-02-18")

        # Test event with minimal information
        self.assertEqual(events[2]['summary'], 'Basketball - Team C at Home')
        self.assertEqual(events[2]['start']['dateTime'], "2024-02-20T17:00:00")

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
            ["Basketball 2025"],  # Sport name row
            ["Date", "Day", "Event", "Location", "Time", "Transportation", "Release", "Departure"],  # Headers
            ["2/10/2025", "Mon", "Team A", "Home", "3:00 PM", "", "", ""],
            ["2/15-17/2025", "Fri-Sun", "Team B", "Away", "TBD", "", "", ""],
            ["2/20/2025", "Wed", "Team C", "Home", "5:00 PM", "", "", ""],
        ]
        events = parse_sports_events(test_data, "Basketball")
        self.assertEqual(len(events), 3)
        
        # Check first event
        self.assertEqual(events[0]['summary'], 'Basketball 2025 - Team A at Home')
        self.assertEqual(events[0]['start']['dateTime'], "2025-02-10T15:00:00")
        
        # Check second event (date range)
        self.assertEqual(events[1]['summary'], 'Basketball 2025 - Team B at Away')
        self.assertEqual(events[1]['start']['date'], "2025-02-15")
        self.assertEqual(events[1]['end']['date'], "2025-02-18")
        
        # Check third event
        self.assertEqual(events[2]['summary'], 'Basketball 2025 - Team C at Home')
        self.assertEqual(events[2]['start']['dateTime'], "2025-02-20T17:00:00")

    def test_parse_sports_events_date_ranges(self):
        # Test data with various date range formats
        test_data = [
            ["Track and Field 2025"],  # Sport name row
            ["Date", "Day", "Event", "Location", "Time", "Transportation", "Release", "Departure"],  # Headers
            ["2/10-13/2025", "Mon-Thu", "TRYOUTS", "SLOHS", "All SLOHS Athletes", "", "", ""],
            ["4/4-5/2025", "Fri-Sat", "Tournament", "SLOHS", "Qualifiers", "", "", ""],
            ["5/7-10/2025", "Wed-Sat", "CIF", "TBD", "all athletes", "", "", ""],
        ]
        
        events = parse_sports_events(test_data, "Track")
        self.assertEqual(len(events), 3)
        
        # Check first event (2/10-13/2025)
        self.assertEqual(events[0]['start']['date'], "2025-02-10")
        self.assertEqual(events[0]['end']['date'], "2025-02-14")  # End date is exclusive
        
        # Check second event (4/4-5/2025)
        self.assertEqual(events[1]['start']['date'], "2025-04-04")
        self.assertEqual(events[1]['end']['date'], "2025-04-06")
        
        # Check third event (5/7-10/2025)
        self.assertEqual(events[2]['start']['date'], "2025-05-07")
        self.assertEqual(events[2]['end']['date'], "2025-05-11")

    def test_parse_sports_events_special_times(self):
        # Test data with various time formats
        test_data = [
            ["Boys Golf 2025"],  # Sport name row
            ["Date", "Day", "Event", "Location", "Time", "Transportation", "Release", "Departure"],  # Headers
            ["3/1/2025", "Mon", "Match", "Cypress Ridge", "2:00 dive, 3:00 swim", "", "", ""],
            ["3/2/2025", "Tue", "Match", "SM Country Club", "3 PM", "", "", ""],
            ["3/3/2025", "Wed", "Match", "SLO CC", "4", "", "", ""],
            ["3/4/2025", "Thu", "Match", "Hunter Ranch", "3:30 (V only)", "", "", ""],
            ["3/5/2025", "Fri", "Match", "Dairy Creek", "Chalk", "", "", ""],  # Invalid time
        ]
        
        events = parse_sports_events(test_data, "Golf")
        self.assertEqual(len(events), 5)
        
        # Check first event (2:00 dive, 3:00 swim)
        self.assertEqual(events[0]['start']['dateTime'], "2025-03-01T14:00:00")
        
        # Check second event (3 PM)
        self.assertEqual(events[1]['start']['dateTime'], "2025-03-02T15:00:00")
        
        # Check third event (4)
        self.assertEqual(events[2]['start']['dateTime'], "2025-03-03T16:00:00")
        
        # Check fourth event (3:30 (V only))
        self.assertEqual(events[3]['start']['dateTime'], "2025-03-04T15:30:00")
        
        # Check fifth event (invalid time - should be all-day)
        self.assertTrue('date' in events[4]['start'])
        self.assertEqual(events[4]['start']['date'], "2025-03-05")

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
        # Test data with locations that could be mistaken for times
        test_data = [
            ["Boys Golf 2025"],  # Sport name row
            ["Date", "Day", "Event", "Location", "Time", "Transportation", "Release", "Departure"],  # Headers
            ["3/1/2025", "Mon", "Match", "SLOHS", "Cypress Ridge", "", "", ""],
            ["3/2/2025", "Tue", "Match", "AGHS", "SM Country Club", "", "", ""],
            ["3/3/2025", "Wed", "Match", "PRHS", "SLO CC", "", "", ""],
        ]
        
        events = parse_sports_events(test_data, "Golf")
        self.assertEqual(len(events), 3)
        
        # All events should be all-day since the "times" are actually locations
        for event in events:
            self.assertTrue('date' in event['start'])
            self.assertEqual(event['description'].split('\n')[1], "Time: TBD")

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

    @patch('googleapiclient.discovery.build')
    def test_create_or_get_sports_calendar(self, mock_build):
        """Test calendar creation and retrieval."""
        # Mock the calendar service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Set up mock calendar list and insert responses
        mock_list = MagicMock()
        mock_insert = MagicMock()
        mock_service.calendarList.return_value.list.return_value.execute.return_value = {
            'items': [{'summary': 'SLOHS Sports', 'id': 'existing_id'}]
        }
        mock_service.calendars.return_value.insert.return_value.execute.return_value = {'id': 'new_id'}
        
        # Test getting existing calendar
        calendar_id = create_or_get_sports_calendar(mock_service, 'SLOHS Sports')
        self.assertEqual(calendar_id, 'existing_id')
        
        # Test creating new calendar
        calendar_id = create_or_get_sports_calendar(mock_service, 'SLOHS Football')
        self.assertEqual(calendar_id, 'new_id')
        
        # Verify calendar creation call
        mock_service.calendars.return_value.insert.assert_called_with(
            body={
                'summary': 'SLOHS Football',
                'description': 'San Luis Obispo High School SLOHS Football Schedule',
                'timeZone': 'America/Los_Angeles',
                'accessRole': 'reader',
                'selected': True
            }
        )

    @patch('googleapiclient.discovery.build')
    def test_delete_all_events(self, mock_build):
        """Test deleting all events from a calendar."""
        # Mock the calendar service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock events list response with pagination
        mock_service.events.return_value.list.return_value.execute.side_effect = [
            {
                'items': [
                    {'id': 'event1', 'summary': 'Event 1'},
                    {'id': 'event2', 'summary': 'Event 2'}
                ],
                'nextPageToken': 'token123'
            },
            {
                'items': [
                    {'id': 'event3', 'summary': 'Event 3'}
                ]
            }
        ]
        
        # Delete events
        delete_all_events(mock_service, 'calendar_id')
        
        # Verify delete calls
        delete_calls = [
            call().delete(calendarId='calendar_id', eventId='event1'),
            call().delete(calendarId='calendar_id', eventId='event2'),
            call().delete(calendarId='calendar_id', eventId='event3')
        ]
        mock_service.events.assert_has_calls(delete_calls, any_order=True)
        self.assertEqual(mock_service.events().delete.call_count, 3)

    @patch('googleapiclient.discovery.build')
    def test_get_event_key(self, mock_build):
        """Test generating unique event keys."""
        # Test with dateTime events
        event1 = {
            'summary': 'Test Event',
            'start': {'dateTime': '2024-02-10T15:00:00'},
            'end': {'dateTime': '2024-02-10T17:00:00'}
        }
        self.assertEqual(
            get_event_key(event1),
            '2024-02-10T15:00:00_2024-02-10T17:00:00_Test Event'
        )

        # Test with date events
        event2 = {
            'summary': 'Test Event',
            'start': {'date': '2024-02-10'},
            'end': {'date': '2024-02-11'}
        }
        self.assertEqual(
            get_event_key(event2),
            '2024-02-10_2024-02-11_Test Event'
        )

    @patch('googleapiclient.discovery.build')
    def test_get_existing_events(self, mock_build):
        """Test fetching and indexing existing events."""
        # Mock the calendar service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock events list response with pagination
        mock_service.events.return_value.list.return_value.execute.side_effect = [
            {
                'items': [
                    {
                        'id': 'event1',
                        'summary': 'Event 1',
                        'start': {'dateTime': '2024-02-10T15:00:00'},
                        'end': {'dateTime': '2024-02-10T17:00:00'}
                    }
                ],
                'nextPageToken': 'token123'
            },
            {
                'items': [
                    {
                        'id': 'event2',
                        'summary': 'Event 2',
                        'start': {'date': '2024-02-11'},
                        'end': {'date': '2024-02-12'}
                    }
                ]
            }
        ]
        
        # Get existing events
        events = get_existing_events(mock_service, 'calendar_id')
        
        # Verify events are indexed by key
        self.assertEqual(len(events), 2)
        key1 = '2024-02-10T15:00:00_2024-02-10T17:00:00_Event 1'
        key2 = '2024-02-11_2024-02-12_Event 2'
        self.assertIn(key1, events)
        self.assertIn(key2, events)
        self.assertEqual(events[key1]['id'], 'event1')
        self.assertEqual(events[key2]['id'], 'event2')

    @patch('googleapiclient.discovery.build')
    def test_update_calendar(self, mock_build):
        """Test updating calendar with new events efficiently."""
        # Mock the calendar service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock existing events
        mock_service.events.return_value.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': 'event1',
                    'summary': 'Event 1',
                    'start': {'dateTime': '2024-02-10T15:00:00'},
                    'end': {'dateTime': '2024-02-10T17:00:00'},
                    'description': 'Test Description'
                }
            ]
        }
        
        # Set up mock responses for insert and update
        mock_service.events.return_value.insert.return_value.execute.return_value = {
            'id': 'new_event_id',
            'htmlLink': 'https://calendar.google.com/event/123'
        }
        
        # Test events
        new_events = [
            {
                'summary': 'Event 1',  # Same as existing
                'start': {'dateTime': '2024-02-10T15:00:00'},
                'end': {'dateTime': '2024-02-10T17:00:00'},
                'description': 'Test Description'
            },
            {
                'summary': 'Event 2',  # New event
                'start': {'dateTime': '2024-02-11T15:00:00'},
                'end': {'dateTime': '2024-02-11T17:00:00'}
            }
        ]
        
        # Update calendar
        update_calendar(mock_service, new_events, 'calendar_id')
        
        # Verify no update was called for unchanged event
        mock_service.events.return_value.update.assert_not_called()
        
        # Verify insert was called for new event
        mock_service.events.return_value.insert.assert_called_once_with(
            calendarId='calendar_id',
            body=new_events[1]
        )
        
        # Verify delete was not called (no events to delete)
        mock_service.events.return_value.delete.assert_not_called()

    @patch('googleapiclient.discovery.build')
    def test_update_calendar_with_changes(self, mock_build):
        """Test updating calendar when events have changed."""
        # Mock the calendar service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock existing events
        mock_service.events.return_value.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': 'event1',
                    'summary': 'Event 1',
                    'start': {'dateTime': '2024-02-10T15:00:00'},
                    'end': {'dateTime': '2024-02-10T17:00:00'},
                    'description': 'Original Description'
                }
            ]
        }
        
        # Test events with changes
        updated_events = [
            {
                'summary': 'Event 1',  # Same summary
                'start': {'dateTime': '2024-02-10T15:00:00'},  # Same start
                'end': {'dateTime': '2024-02-10T17:00:00'},  # Same end
                'description': 'Updated Description'  # Changed description
            }
        ]
        
        # Update calendar
        update_calendar(mock_service, updated_events, 'calendar_id')
        
        # Verify update was called for changed event
        mock_service.events.return_value.update.assert_called_once_with(
            calendarId='calendar_id',
            eventId='event1',
            body=updated_events[0]
        )
        
        # Verify no insert or delete was called
        mock_service.events.return_value.insert.assert_not_called()
        mock_service.events.return_value.delete.assert_not_called()

    @patch('googleapiclient.discovery.build')
    def test_update_calendar_with_deletions(self, mock_build):
        """Test updating calendar when events need to be deleted."""
        # Mock the calendar service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock existing events
        mock_service.events.return_value.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': 'event1',
                    'summary': 'Event 1',
                    'start': {'dateTime': '2024-02-10T15:00:00'},
                    'end': {'dateTime': '2024-02-10T17:00:00'}
                }
            ]
        }
        
        # Test events (empty list means all events should be deleted)
        new_events = []
        
        # Update calendar
        update_calendar(mock_service, new_events, 'calendar_id')
        
        # Verify delete was called for obsolete event
        mock_service.events.return_value.delete.assert_called_once_with(
            calendarId='calendar_id',
            eventId='event1'
        )
        
        # Verify no insert or update was called
        mock_service.events.return_value.insert.assert_not_called()
        mock_service.events.return_value.update.assert_not_called()

    def test_event_key_generation(self):
        """Test event key generation for different date formats."""
        # Test all-day event
        all_day_event = {
            'summary': 'Test Event',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'}
        }
        self.assertEqual(get_event_key(all_day_event), '2025-03-15_2025-03-16_Test Event')

        # Test timed event
        timed_event = {
            'summary': 'Test Event',
            'start': {'dateTime': '2025-03-15T14:00:00-07:00'},
            'end': {'dateTime': '2025-03-15T16:00:00-07:00'}
        }
        self.assertEqual(get_event_key(timed_event), '2025-03-15_2025-03-15_Test Event')

        # Test event with different timezone
        timed_event_tz = {
            'summary': 'Test Event',
            'start': {'dateTime': '2025-03-15T14:00:00-08:00'},
            'end': {'dateTime': '2025-03-15T16:00:00-08:00'}
        }
        self.assertEqual(get_event_key(timed_event_tz), '2025-03-15_2025-03-15_Test Event')

    def test_event_comparison(self):
        """Test event comparison logic."""
        # Test identical all-day events
        event1 = {
            'summary': 'Test Event',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'},
            'description': 'Test Description'
        }
        event2 = {
            'summary': 'Test Event',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'},
            'description': 'Test Description'
        }
        self.assertTrue(events_are_equal(event1, event2))

        # Test identical timed events with different timezones
        event3 = {
            'summary': 'Test Event',
            'start': {'dateTime': '2025-03-15T14:00:00-07:00'},
            'end': {'dateTime': '2025-03-15T16:00:00-07:00'},
            'description': 'Test Description'
        }
        event4 = {
            'summary': 'Test Event',
            'start': {'dateTime': '2025-03-15T14:00:00-08:00'},
            'end': {'dateTime': '2025-03-15T16:00:00-08:00'},
            'description': 'Test Description'
        }
        self.assertTrue(events_are_equal(event3, event4))

        # Test different events
        event5 = {
            'summary': 'Different Event',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'},
            'description': 'Test Description'
        }
        self.assertFalse(events_are_equal(event1, event5))

        # Test events with different descriptions
        event6 = {
            'summary': 'Test Event',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'},
            'description': 'Different Description'
        }
        self.assertFalse(events_are_equal(event1, event6))

        # Test events with different dates
        event7 = {
            'summary': 'Test Event',
            'start': {'date': '2025-03-16'},
            'end': {'date': '2025-03-17'},
            'description': 'Test Description'
        }
        self.assertFalse(events_are_equal(event1, event7))

        # Test events with missing fields
        event8 = {
            'summary': 'Test Event',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'}
        }
        self.assertFalse(events_are_equal(event1, event8))

        # Test events with None values
        event9 = {
            'summary': 'Test Event',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'},
            'description': None
        }
        self.assertFalse(events_are_equal(event1, event9))

    def test_edge_cases(self):
        """Test edge cases in event comparison."""
        # Test events with empty strings
        event1 = {
            'summary': '',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'},
            'description': ''
        }
        event2 = {
            'summary': '',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'},
            'description': ''
        }
        self.assertTrue(events_are_equal(event1, event2))

        # Test events with whitespace differences
        event3 = {
            'summary': '  Test Event  ',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'},
            'description': '  Test Description  '
        }
        event4 = {
            'summary': 'Test Event',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'},
            'description': 'Test Description'
        }
        self.assertTrue(events_are_equal(event3, event4))

        # Test events with different date formats but same date
        event5 = {
            'summary': 'Test Event',
            'start': {'date': '2025-03-15'},
            'end': {'date': '2025-03-16'},
            'description': 'Test Description'
        }
        event6 = {
            'summary': 'Test Event',
            'start': {'dateTime': '2025-03-15T00:00:00-07:00'},
            'end': {'dateTime': '2025-03-16T00:00:00-07:00'},
            'description': 'Test Description'
        }
        self.assertTrue(events_are_equal(event5, event6))

class TestDateRangeParsing(unittest.TestCase):
    def setUp(self):
        # Create a sample sheet with different date range formats
        self.test_sheet = [
            ["Test Sport"],  # Sport name row
            ["Date", "Time", "Opponent", "Location"],  # Headers
            ["2/17-20/2025", "All Day", "Tournament 1", "Location 1"],  # 4-day range with year
            ["2/10-14", "All Day", "Tournament 2", "Location 2"],  # 5-day range same month
            ["4/30-5/2", "All Day", "Tournament 3", "Location 3"],  # Cross-month range
            ["5/27-5/31/24", "All Day", "Tournament 4", "Location 4"],  # Full date range with 2-digit year
            ["4/25-26/2025", "All Day", "Tournament 5", "Location 5"],  # 2-day range with year
            ["12/31-1/2", "All Day", "Tournament 6", "Location 6"],  # Year transition
            ["2/15", "3:30 PM", "Single Day", "Location 7"],  # Single day event
            ["2/17-25/2025", "All Day", "Too Long", "Location 8"],  # Too long range (should be skipped)
        ]
        
        # Suppress log output during tests
        logging.getLogger().setLevel(logging.ERROR)
    
    def test_four_day_range_with_year(self):
        """Test format: 2/17-20/2025"""
        events = parse_sports_events(self.test_sheet, "Test Sheet")
        event = self._find_event(events, "Tournament 1")
        self.assertIsNotNone(event)
        self.assertEqual(event['start']['date'], "2025-02-17")
        self.assertEqual(event['end']['date'], "2025-02-21")  # End date is exclusive
        
    def test_same_month_range(self):
        """Test format: 2/10-14"""
        events = parse_sports_events(self.test_sheet, "Test Sheet")
        event = self._find_event(events, "Tournament 2")
        self.assertIsNotNone(event)
        self.assertEqual(event['start']['date'], "2025-02-10")
        self.assertEqual(event['end']['date'], "2025-02-15")
        
    def test_cross_month_range(self):
        """Test format: 4/30-5/2"""
        events = parse_sports_events(self.test_sheet, "Test Sheet")
        event = self._find_event(events, "Tournament 3")
        self.assertIsNotNone(event)
        self.assertEqual(event['start']['date'], "2025-04-30")
        self.assertEqual(event['end']['date'], "2025-05-03")
        
    def test_full_range_with_two_digit_year(self):
        """Test format: 5/27-5/31/24"""
        events = parse_sports_events(self.test_sheet, "Test Sheet")
        event = self._find_event(events, "Tournament 4")
        self.assertIsNotNone(event)
        self.assertEqual(event['start']['date'], "2025-05-27")  # Should use default year 2025
        self.assertEqual(event['end']['date'], "2025-06-01")
        
    def test_two_day_range_with_year(self):
        """Test format: 4/25-26/2025"""
        events = parse_sports_events(self.test_sheet, "Test Sheet")
        event = self._find_event(events, "Tournament 5")
        self.assertIsNotNone(event)
        self.assertEqual(event['start']['date'], "2025-04-25")
        self.assertEqual(event['end']['date'], "2025-04-27")
        
    def test_year_transition_range(self):
        """Test format: 12/31-1/2"""
        events = parse_sports_events(self.test_sheet, "Test Sheet")
        event = self._find_event(events, "Tournament 6")
        self.assertIsNotNone(event)
        # Should handle year transition
        self.assertEqual(event['start']['date'], "2025-12-31")
        self.assertEqual(event['end']['date'], "2026-01-03")
        
    def test_single_day_event(self):
        """Test format: 2/15"""
        events = parse_sports_events(self.test_sheet, "Test Sheet")
        event = self._find_event(events, "Single Day")
        self.assertIsNotNone(event)
        # Should be a timed event
        self.assertTrue('dateTime' in event['start'])
        self.assertEqual(
            datetime.fromisoformat(event['start']['dateTime']).strftime('%Y-%m-%d %H:%M'),
            "2025-02-15 15:30"
        )
        
    def test_too_long_range(self):
        """Test format: 2/17-25/2025 (should be skipped as > 7 days)"""
        events = parse_sports_events(self.test_sheet, "Test Sheet")
        event = self._find_event(events, "Too Long")
        self.assertIsNone(event)
        
    def test_invalid_dates(self):
        """Test invalid date formats"""
        invalid_sheet = [
            ["Test Sport"],
            ["Date", "Time", "Opponent", "Location"],
            ["13/1-2", "All Day", "Invalid Month", "Location"],  # Invalid month
            ["2/32-33", "All Day", "Invalid Day", "Location"],   # Invalid day
            ["2/15-14", "All Day", "Backwards Range", "Location"],  # End before start
            ["not a date", "All Day", "Invalid Format", "Location"],  # Invalid format
        ]
        events = parse_sports_events(invalid_sheet, "Test Sheet")
        self.assertEqual(len(events), 0)  # No events should be created
        
    def _find_event(self, events, opponent_name):
        """Helper to find an event by opponent name"""
        for event in events:
            if opponent_name in event['summary']:
                return event
        return None

if __name__ == '__main__':
    unittest.main() 