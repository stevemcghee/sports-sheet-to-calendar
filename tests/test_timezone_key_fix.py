import sys
import os
import unittest
from datetime import datetime

# Add parent directory to path so we can import calendar_sync
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calendar_sync import get_event_key

class TestTimezoneKeyFix(unittest.TestCase):
    def test_key_consistency_across_timezones(self):
        # Event in Pacific time (what we parse from sheet)
        # 2026-02-24 16:30:00 -08:00
        event_local = {
            "summary": "Morro Bay at MBHS",
            "start": {"dateTime": "2026-02-24T16:30:00-08:00"}
        }

        # Event in UTC (what we get from Google Calendar)
        # 2026-02-25 00:30:00 Z (equivalent to above)
        event_utc = {
            "summary": "Morro Bay at MBHS",
            "start": {"dateTime": "2026-02-25T00:30:00Z"}
        }

        key_local = get_event_key(event_local)
        key_utc = get_event_key(event_utc)

        print(f"Key Local: {key_local}")
        print(f"Key UTC:   {key_utc}")

        # They should be identical now: 2026-02-24_Morro Bay at MBHS
        self.assertEqual(key_local, key_utc)
        self.assertEqual(key_local, "2026-02-24_Morro Bay at MBHS")

if __name__ == '__main__':
    unittest.main()
