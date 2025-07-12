"""Unit tests for flight search functionality."""
import json
import os
import unittest
from unittest.mock import patch, MagicMock

# Import the module to test
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.insert(0, project_root)

from src.mcp.flight_search_mcp import FlightSearchMCP


class TestFlightSearchMCP(unittest.TestCase):
    """Test cases for FlightSearchMCP class."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before any tests in this class run."""
        # Load test data from JSON file
        test_data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'fixtures',
            'flight_search_response.json'
        )
        with open(test_data_path, 'r', encoding='utf-8') as f:
            cls.test_data = json.load(f)

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock for the API client
        self.mock_client = MagicMock()
        self.mock_client.shopping.flight_offers_search.return_value = self.test_data
        
        # Initialize the class under test with the mock client
        self.flight_search = FlightSearchMCP(client=self.mock_client)

    def test_total_price_calculation(self):
        """Test that total price is correctly calculated from the response."""
        # Call the method under test
        results = self.flight_search.search_flights(
            origin='DEL',
            destination='BOM',
            departure_date='2025-08-01',
            adults=1
        )
        
        # Verify the total price is correctly extracted
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['price']['total'], '350.00')
        self.assertEqual(results[1]['price']['total'], '400.00')

    def test_segment_information(self):
        """Test that segment information is correctly extracted."""
        results = self.flight_search.search_flights(
            origin='DEL',
            destination='BOM',
            departure_date='2025-08-01',
            adults=1
        )
        
        # Check segments for the first flight
        first_flight = results[0]
        self.assertEqual(len(first_flight['itineraries']), 1)
        self.assertEqual(len(first_flight['itineraries'][0]['segments']), 1)
        
        segment = first_flight['itineraries'][0]['segments'][0]
        self.assertEqual(segment['departure']['iataCode'], 'DEL')
        self.assertEqual(segment['arrival']['iataCode'], 'BOM')
        self.assertEqual(segment['carrierCode'], 'AI')
        self.assertEqual(segment['number'], '101')
        self.assertEqual(segment['price']['amount'], '150.00')

    def test_sorting_by_price(self):
        """Test that results are correctly sorted by price."""
        results = self.flight_search.search_flights(
            origin='DEL',
            destination='BOM',
            departure_date='2025-08-01',
            adults=1,
            sort_by='price'
        )
        
        # Verify results are sorted by price (ascending)
        self.assertEqual(len(results), 2)
        self.assertLessEqual(
            float(results[0]['price']['total']),
            float(results[1]['price']['total'])
        )
        self.assertEqual(results[0]['id'], '1')  # Cheaper flight first
        self.assertEqual(results[1]['id'], '2')  # More expensive flight second

    def test_sorting_by_duration(self):
        """Test that results are correctly sorted by duration."""
        results = self.flight_search.search_flights(
            origin='DEL',
            destination='BOM',
            departure_date='2025-08-01',
            adults=1,
            sort_by='duration'
        )
        
        # Verify results are sorted by duration (shortest first)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], '1')  # Shorter duration (2h30m)
        self.assertEqual(results[1]['id'], '2')  # Longer duration (3h15m)

    def test_empty_response(self):
        """Test handling of empty response from the API."""
        # Configure mock to return empty data
        self.mock_client.shopping.flight_offers_search.return_value = {
            'meta': {'count': 0},
            'data': []
        }
        
        results = self.flight_search.search_flights(
            origin='XXX',  # Invalid origin
            destination='YYY',  # Invalid destination
            departure_date='2025-08-01',
            adults=1
        )
        
        self.assertEqual(len(results), 0)

    def test_api_error_handling(self):
        """Test proper handling of API errors."""
        # Configure mock to raise an exception
        self.mock_client.shopping.flight_offers_search.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception) as context:
            self.flight_search.search_flights(
                origin='DEL',
                destination='BOM',
                departure_date='2025-08-01',
                adults=1
            )
        
        self.assertIn("API Error", str(context.exception))



if __name__ == '__main__':
    unittest.main()
