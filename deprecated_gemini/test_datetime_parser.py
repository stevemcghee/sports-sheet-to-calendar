import unittest
from datetime import datetime
import pytz
from datetime_parser import parse_datetime_with_gemini, parse_datetime_range_with_gemini
import os
from dotenv import load_dotenv

class TestDatetimeParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv()
        if not os.getenv('GEMINI_API_KEY'):
            raise ValueError("GEMINI_API_KEY not found in environment variables")

    def test_parse_single_datetime(self):
        """Test parsing various single datetime formats."""
        test_cases = [
            "2024-05-01 14:30",  # Basic datetime
            "5/1/24 2:30 PM",    # US format with AM/PM
            "May 1, 2024 2:30pm", # Written month
            "next Monday 3pm",    # Relative date
            "tomorrow 9am",       # Relative date
            "2024-05-01",         # Date only
            "3pm",                # Time only (should use today's date)
            "next week Monday",   # Relative date only
        ]

        for dt_str in test_cases:
            with self.subTest(datetime_str=dt_str):
                result = parse_datetime_with_gemini(dt_str)
                
                # Verify result is valid ISO format
                dt = datetime.fromisoformat(result)
                
                # Verify timezone is US/Pacific (compare UTC offset to expected Pacific offset for that date)
                expected_offset = datetime.now(pytz.timezone('America/Los_Angeles')).utcoffset()
                self.assertEqual(dt.utcoffset(), expected_offset)
                
                print(f"\nInput: {dt_str}")
                print(f"Parsed: {result}")

    def test_parse_datetime_range(self):
        """Test parsing various datetime range formats."""
        test_cases = [
            "2024-05-01 14:30 - 16:30",  # Basic time range
            "5/1/24 2:30 PM - 4:30 PM",  # US format with AM/PM
            "May 1-3, 2024",             # Date range
            "next Monday 3pm - 5pm",      # Relative date with time range
            "tomorrow 9am - 5pm",         # Relative date with time range
            "2024-05-01 - 2024-05-03",   # Date range
            "3pm - 5pm",                  # Time range (should use today's date)
            "next week Monday - Friday",  # Relative date range
        ]

        for dt_str in test_cases:
            with self.subTest(datetime_str=dt_str):
                start, end = parse_datetime_range_with_gemini(dt_str)
                
                # Verify results are valid ISO format
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                
                # Verify timezone is US/Pacific (compare UTC offset to expected Pacific offset for that date)
                expected_offset = datetime.now(pytz.timezone('America/Los_Angeles')).utcoffset()
                self.assertEqual(start_dt.utcoffset(), expected_offset)
                self.assertEqual(end_dt.utcoffset(), expected_offset)
                
                # Verify end is after start
                self.assertGreater(end_dt, start_dt)
                
                print(f"\nInput: {dt_str}")
                print(f"Start: {start}")
                print(f"End: {end}")

    def test_invalid_inputs(self):
        """Test handling of invalid inputs."""
        invalid_inputs = [
            ("", False),                     # Empty string, Gemini returns today
            ("invalid date", True),         # Invalid format, Gemini returns error
            ("not a date at all", False),   # Gemini returns today
            ("12345", False),               # Gemini returns today
        ]

        for dt_str, should_raise in invalid_inputs:
            with self.subTest(datetime_str=dt_str):
                if should_raise:
                    with self.assertRaises(ValueError):
                        parse_datetime_with_gemini(dt_str)
                    with self.assertRaises(ValueError):
                        parse_datetime_range_with_gemini(dt_str)
                else:
                    # Should return a valid ISO datetime string
                    result = parse_datetime_with_gemini(dt_str)
                    try:
                        dt = datetime.fromisoformat(result)
                    except Exception:
                        self.fail(f"Did not return valid ISO datetime for input: {dt_str}")
                    # For range, should return two valid ISO datetimes
                    start, end = parse_datetime_range_with_gemini(dt_str)
                    try:
                        dt_start = datetime.fromisoformat(start)
                        dt_end = datetime.fromisoformat(end)
                    except Exception:
                        self.fail(f"Did not return valid ISO datetime range for input: {dt_str}")

if __name__ == '__main__':
    unittest.main() 