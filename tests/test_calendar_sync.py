import unittest
from datetime import date
from calendar_sync import parse_date

class TestCalendarSync(unittest.TestCase):

    def test_parse_date_range_single_month(self):
        """Test parsing a date range within a single month."""
        start_date, end_date = parse_date("2/15-17/2025")
        self.assertEqual(start_date, date(2025, 2, 15))
        self.assertEqual(end_date, date(2025, 2, 17))

    def test_parse_date_range_multiple_months(self):
        """Test parsing a date range spanning multiple months."""
        start_date, end_date = parse_date("7/28-8/1/2025")
        self.assertEqual(start_date, date(2025, 7, 28))
        self.assertEqual(end_date, date(2025, 8, 1))

    def test_parse_date_range_multiple_years(self):
        """Test parsing a date range spanning multiple years."""
        start_date, end_date = parse_date("12/28/2024-1/5/2025")
        self.assertEqual(start_date, date(2024, 12, 28))
        self.assertEqual(end_date, date(2025, 1, 5))

    def test_parse_date_range_invalid_format(self):
        """Test that an invalid date range format raises a ValueError."""
        with self.assertRaises(ValueError):
            parse_date("1-2-2025")

if __name__ == '__main__':
    unittest.main()