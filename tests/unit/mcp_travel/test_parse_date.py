"""Unit tests for parseDate function."""
import unittest
from datetime import datetime, timedelta

# Import the module to test
import sys
import os
# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.insert(0, project_root)

from src.mcp_travel.mcp_utils import parseDate

class TestParseDate(unittest.TestCase):
    """Test cases for parseDate function."""

    def test_parse_relative_date(self):
        """Test parsing relative dates like 'tomorrow'."""
        # Test with 'tomorrow'
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.assertEqual(parseDate("tomorrow"), tomorrow)

    def test_parse_formatted_dates(self):
        """Test parsing already formatted date strings."""
        # Test with different date formats
        test_cases = [
            ("2025-12-31", "%Y-%m-%d", "2025-12-31"),
            ("12/31/2025", "%m/%d/%Y", "12/31/2025"),
            ("31/12/2025", "%d/%m/%Y", "31/12/2025"),
            ("20251231", "%Y%m%d", "20251231"),
            # Test format conversion
            ("2025-12-31", "%d/%m/%Y", "31/12/2025"),
            ("12/31/2025", "%Y-%m-%d", "2025-12-31"),
        ]
        
        for date_str, output_format, expected in test_cases:
            with self.subTest(date_str=date_str, format=output_format):
                result = parseDate(date_str, output_format)
                self.assertEqual(result, expected)

    def test_invalid_date(self):
        """Test handling of invalid date strings."""
        # Should return today's date for invalid input
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(parseDate("not a valid date"), today)
        
        # Test with invalid date that doesn't match any format
        self.assertEqual(parseDate("2025-13-45"), today)  # Invalid date
        self.assertEqual(parseDate("99/99/9999"), today)  # Invalid date

if __name__ == '__main__':
    unittest.main()
