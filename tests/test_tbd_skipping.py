import sys
import os
import unittest
from unittest.mock import MagicMock

# Add parent directory to path so we can import calendar_sync
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calendar_sync import parse_sports_events

class TestTBDSkipping(unittest.TestCase):
    def test_skip_tba_tbd(self):
        data = [
            ['Date', 'Event', 'Location', 'Time'], # Header
            ['2/24/2026', 'Real Game', 'Home', '4:30 PM'],
            ['TBA', 'Unknown Game', 'Away', 'TBD'],
            ['TBD', 'Future Game', 'SLOHS', '5:00 PM'],
            ['02/25/2026', 'Another Game', 'Away', '6:00 PM']
        ]
        
        # Mocking sheet_name
        events = parse_sports_events(data, "Test Sport")
        
        # Should only have 2 events (Real Game and Another Game)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['summary'], 'Real Game at Home')
        self.assertEqual(events[1]['summary'], 'Another Game at Away')
        
        summaries = [e['summary'] for e in events]
        self.assertNotIn('Unknown Game at Away', summaries)
        self.assertNotIn('Future Game at SLOHS', summaries)

if __name__ == '__main__':
    unittest.main()
