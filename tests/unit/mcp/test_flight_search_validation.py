"""Unit tests for flight search parameter validation."""
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

from src.mcp.flight_search_mcp import FlightSearchMCP, is_valid_date_format, validate_return_date


class TestFlightSearchValidation(unittest.TestCase):
    """Test cases for flight search parameter validation."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.flight_search = FlightSearchMCP(client=MagicMock())

    # Test _validate_airport_code
    def test_validate_airport_code_valid(self):
        """Test valid airport codes."""
        valid_codes = ['SFO', 'JFK', 'LAX', 'LHR', 'CDG']
        for code in valid_codes:
            with self.subTest(code=code):
                try:
                    self.flight_search._validate_airport_code(code, "test_param")
                except ValueError:
                    self.fail(f"_validate_airport_code() raised ValueError for valid code: {code}")

    def test_validate_airport_code_invalid(self):
        """Test invalid airport codes."""
        invalid_cases = [
            ('sfo', "lowercase"),
            ('SfO', "mixed case"),
            ('123', "numbers"),
            ('SFO1', "too long"),
            ('SF', "too short"),
            ('S@F', "special chars"),
            ('', "empty string"),
            (None, "None"),
            (123, "integer")
        ]
        for code, description in invalid_cases:
            with self.subTest(description=description, code=code):
                with self.assertRaises(ValueError):
                    self.flight_search._validate_airport_code(code, "test_param")

    # Test _validate_passenger_count
    def test_validate_passenger_count_valid(self):
        """Test valid passenger counts."""
        valid_cases = [
            (1, 0, 0),  # Min adults, no children/infants
            (9, 0, 0),  # Max adults
            (2, 0, 2),  # Adults with max infants
            (2, 7, 0),  # Adults with max children
            (5, 3, 1),  # Mixed passengers within limits
            (1, 0, 1),  # One adult with one infant
        ]
        for adults, children, infants in valid_cases:
            with self.subTest(adults=adults, children=children, infants=infants):
                try:
                    self.flight_search._validate_passenger_count(adults, children, infants)
                except ValueError:
                    self.fail("_validate_passenger_count() raised ValueError for valid input")

    def test_validate_passenger_count_invalid(self):
        """Test invalid passenger counts."""
        invalid_cases = [
            (0, 0, 0, "no passengers"),
            (10, 0, 0, "too many adults"),
            (1, 9, 0, "too many children"),
            (1, 0, 6, "too many infants"),
            (5, 5, 5, "total exceeds limit"),
            (1, 0, 2, "more infants than adults"),
            (-1, 0, 0, "negative adults"),
            (1, -1, 0, "negative children"),
            (1, 0, -1, "negative infants"),
            (1.5, 0, 0, "non-integer adults"),
            (1, 2.5, 0, "non-integer children"),
            (1, 0, 1.5, "non-integer infants")
        ]
        for adults, children, infants, description in invalid_cases:
            with self.subTest(description=description):
                with self.assertRaises(ValueError):
                    self.flight_search._validate_passenger_count(adults, children, infants)

    # Test _validate_travel_class
    def test_validate_travel_class_valid(self):
        """Test valid travel classes."""
        valid_classes = ['ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST']
        for travel_class in valid_classes:
            with self.subTest(travel_class=travel_class):
                try:
                    self.flight_search._validate_travel_class(travel_class)
                    # Test case insensitivity
                    self.flight_search._validate_travel_class(travel_class.lower())
                except ValueError:
                    self.fail(f"_validate_travel_class() raised ValueError for valid class: {travel_class}")

    def test_validate_travel_class_invalid(self):
        """Test invalid travel classes."""
        invalid_cases = [
            'economy class',
            'BUSINESS_CLASS',
            'FIRST CLASS',
            '',
            None,
            123,
            'ECON',
            'PREMIUM'
        ]
        for travel_class in invalid_cases:
            with self.subTest(travel_class=travel_class):
                with self.assertRaises(ValueError):
                    self.flight_search._validate_travel_class(travel_class)



    # Test is_valid_date_format
    def test_is_valid_date_format_valid(self):
        """Test valid date formats."""
        valid_dates = [
            '2025-01-01',
            '2025-12-31',
            '2024-02-29'  # Leap year
        ]
        for date_str in valid_dates:
            with self.subTest(date_str=date_str):
                self.assertTrue(is_valid_date_format(date_str))

    def test_is_valid_date_format_invalid(self):
        """Test invalid date formats."""
        invalid_cases = [
            ('2025/01/01', "wrong separator"),
            ('01-01-2025', "wrong order"),
            ('2025-13-01', "invalid month"),
            ('2025-01-32', "invalid day"),
            ('2025-02-30', "invalid date (non-leap year)"),
            ('25-01-01', "short year"),
            ('2025-1-1', "single digit month/day"),
            ('', "empty string"),
            (None, "None"),
            (20250101, "integer")
        ]
        for date_str, description in invalid_cases:
            with self.subTest(description=description, date_str=date_str):
                self.assertFalse(is_valid_date_format(date_str))

    # Test validate_return_date
    def test_validate_return_date_valid(self):
        """Test valid return dates."""
        valid_cases = [
            ('2025-07-20', '2025-07-21'),  # Next day
            ('2025-07-20', '2025-07-20'),  # Same day
            ('2025-07-20', '2026-01-01'),  # Far future
            (None, '2025-07-20')  # No return date
        ]
        for start_date, end_date in valid_cases:
            with self.subTest(start_date=start_date, end_date=end_date):
                try:
                    validate_return_date(end_date, start_date)
                except ValueError:
                    self.fail(f"validate_return_date() raised ValueError for valid dates: {start_date} to {end_date}")

    def test_validate_return_date_invalid(self):
        """Test invalid return dates."""
        invalid_cases = [
            ('2025-07-20', '2025-07-19', "return before departure"),
            ('2025-07-20', '2025/07/21', "wrong format"),
            ('2025-07-20', '2025-13-21', "invalid month"),
            ('2025-07-20', '2025-07-32', "invalid day")
        ]
        for start_date, end_date, description in invalid_cases:
            with self.subTest(description=description, start_date=start_date, end_date=end_date):
                with self.assertRaises(ValueError):
                    validate_return_date(end_date, start_date)


if __name__ == "__main__":
    unittest.main()
