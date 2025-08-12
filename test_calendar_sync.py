# All date ranges in these tests are INCLUSIVE
# For example:
# - A range of "2/15-17/2025" means the event spans from Feb 15 through Feb 17 (inclusive)
# - A single day event like "2/15/2025" spans that entire day
# - A range like "4/30-5/2" spans from April 30 through May 2 (inclusive)

import unittest
from datetime import date
from calendar_sync import parse_date

class TestDateParsing(unittest.TestCase):

    def test_parse_date_single_day(self):
        start_date, end_date = parse_date("8/4/2025")
        self.assertEqual(start_date, date(2025, 8, 4))
        self.assertIsNone(end_date)

    def test_parse_date_range_full(self):
        start_date, end_date = parse_date("8/4 - 8/7/2025")
        self.assertEqual(start_date, date(2025, 8, 4))
        self.assertEqual(end_date, date(2025, 8, 7))

    def test_parse_date_range_shorthand_year(self):
        start_date, end_date = parse_date("8/4/25")
        self.assertEqual(start_date, date(2025, 8, 4))
        self.assertIsNone(end_date)

    def test_parse_date_range_no_year(self):
        start_date, end_date = parse_date("8/4 - 8/7")
        current_year = date.today().year
        self.assertEqual(start_date, date(current_year, 8, 4))
        self.assertEqual(end_date, date(current_year, 8, 7))

    def test_parse_date_range_shorthand_day(self):
        start_date, end_date = parse_date("9/5-6")
        current_year = date.today().year
        self.assertEqual(start_date, date(current_year, 9, 5))
        self.assertEqual(end_date, date(current_year, 9, 6))

    def test_parse_date_range_shorthand_day_with_year(self):
        start_date, end_date = parse_date("2/15-17/2025")
        self.assertEqual(start_date, date(2025, 2, 15))
        self.assertEqual(end_date, date(2025, 2, 17))

    def test_invalid_date_format(self):
        with self.assertRaises(ValueError):
            parse_date("invalid date")

    def test_week_of_format(self):
        with self.assertRaises(ValueError):
            parse_date("week of 4/28/2025")

    def test_or_format(self):
        with self.assertRaises(ValueError):
            parse_date("5/12 or 5/13/2025")

    def test_parse_date_range_shorthand_day_2(self):
        start_date, end_date = parse_date("8/4-8/8")
        current_year = date.today().year
        self.assertEqual(start_date, date(current_year, 8, 4))
        self.assertEqual(end_date, date(current_year, 8, 8))

if __name__ == '__main__':
    unittest.main() 