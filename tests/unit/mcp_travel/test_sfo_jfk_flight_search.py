"""Unit tests for SFO to JFK flight search functionality."""
import json
import os
import sys
import unittest
from unittest.mock import MagicMock

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.insert(0, project_root)

from src.mcp_travel.flight_search_mcp import FlightSearchMCP

class TestSFOJFKFlightSearch(unittest.TestCase):
    """Test cases for SFO to JFK flight search response."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before any tests in this class run."""
        # Load test data from JSON file
        test_data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'fixtures',
            'flight_searcch_response_sfo_jfk.json'
        )
        with open(test_data_path, 'r', encoding='utf-8') as f:
            cls.test_data = json.load(f)

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock for the API client
        self.mock_client = MagicMock()
        
        # Create a mock response object with data attribute
        self.mock_response = MagicMock()
        self.mock_response.data = self.test_data
        self.mock_response.meta = {'count': len(self.test_data) if self.test_data else 0}
        
        # Configure the client to return our mock response
        self.mock_client.shopping.flight_offers_search.get.return_value = self.mock_response
        
        # Initialize the class under test with the mock client
        self.flight_search = FlightSearchMCP(client=self.mock_client)

    def test_flight_count(self):
        """Test that the correct number of flights are returned."""
        results = self.flight_search.search_flights(
            source='SFO',
            destination='JFK',
            travel_date='2025-07-20',
            adults=1
        )
        self.assertEqual(len(results), 5)  # Should have 5 flight offers

    def test_flight_segments(self):
        """Test that flight segments are correctly parsed."""
        results = self.flight_search.search_flights(
            source='SFO',
            destination='JFK',
            travel_date='2025-07-20',
            adults=1
        )
        
        # Test first flight's segments
        first_flight = results[0]
        self.assertIn('itineraries', first_flight)
        self.assertGreaterEqual(len(first_flight['itineraries']), 1)
        
        segments = first_flight['itineraries'][0]['segments']
        self.assertGreaterEqual(len(segments), 1)
        
        # Test segment details
        segment = segments[0]
        self.assertIn('departure', segment)
        self.assertIn('iataCode', segment['departure'])
        self.assertIn('at', segment['departure'])
        
        self.assertIn('arrival', segment)
        self.assertIn('iataCode', segment['arrival'])
        self.assertIn('at', segment['arrival'])
        
        self.assertIn('carrierCode', segment)
        self.assertIn('number', segment)

    def test_pricing_information(self):
        """Test that pricing information is correctly parsed."""
        results = self.flight_search.search_flights(
            source='SFO',
            destination='JFK',
            travel_date='2025-07-20',
            adults=1
        )
        
        # Test first flight's pricing
        first_flight = results[0]
        self.assertIn('price', first_flight)
        self.assertIn('total', first_flight['price'])
        self.assertIn('currency', first_flight['price'])

    def test_traveler_pricing(self):
        """Test that traveler pricing information is correctly parsed."""
        results = self.flight_search.search_flights(
            source='SFO',
            destination='JFK',
            travel_date='2025-07-20',
            adults=1,
        )
        
        first_flight = results[0]
        self.assertIn('travelerPricings', first_flight)
        
        # Should have pricing for both adult and child
        traveler_types = {tp['travelerType'] for tp in first_flight['travelerPricings']}
        self.assertIn('ADULT', traveler_types)
        self.assertIn('CHILD', traveler_types)

    def test_flight_duration(self):
        """Test that flight duration is correctly calculated."""
        results = self.flight_search.search_flights(
            source='SFO',
            destination='JFK',
            travel_date='2025-07-20',
            adults=1
        )
        
        first_flight = results[0]
        self.assertIn('itineraries', first_flight)
        self.assertIn('duration', first_flight['itineraries'][0])
        
        # Duration should be in ISO 8601 format (e.g., 'PT8H27M')
        duration = first_flight['itineraries'][0]['duration']
        self.assertTrue(duration.startswith('PT'))
        self.assertIn('H', duration)  # Should have hours

    def test_sort_by_duration(self):
        """Test that flights are correctly sorted by duration (shortest first)."""
        # Get results sorted by duration
        results = self.flight_search.search_flights(
            source='SFO',
            destination='JFK',
            travel_date='2025-07-20',
            adults=1,
            sort_func=self.flight_search.sort_by_duration
        )
        
        # Verify we have multiple results to sort
        self.assertGreater(len(results), 1, "Need multiple flights to test sorting")
        
        # Extract durations and verify they're in ascending order
        import isodate
        durations = []
        for flight in results:
            duration_str = flight['itineraries'][0]['duration']
            # Convert ISO 8601 duration to minutes for comparison using isodate
            duration = isodate.parse_duration(duration_str)
            minutes = int(duration.total_seconds() // 60)
            durations.append(minutes)
        
        # Check if durations are in non-decreasing order
        for i in range(len(durations) - 1):
            self.assertLessEqual(durations[i], durations[i + 1],
                               f"Flights not sorted by duration. {durations[i]} > {durations[i+1]}")

    def test_sort_by_price(self):
        """Test that flights are correctly sorted by price (cheapest first)."""
        # Get results sorted by price
        results = self.flight_search.search_flights(
            source='SFO',
            destination='JFK',
            travel_date='2025-07-20',
            adults=2,
            sort_func=self.flight_search.sort_by_price
        )
        
        # Verify we have multiple results to sort
        self.assertGreater(len(results), 1, "Need multiple flights to test sorting")
        
        # Extract prices and verify they're in ascending order
        prices = [float(flight['price']['total']) for flight in results]
        
        # Check if prices are in non-decreasing order
        for i in range(len(prices) - 1):
            self.assertLessEqual(prices[i], prices[i + 1],
                               f"Flights not sorted by price. {prices[i]} > {prices[i+1]}")
    
    def test_sort_by_departure_time(self):
        """Test that flights are correctly sorted by departure time (earliest first)."""
        # Get results sorted by departure time
        results = self.flight_search.search_flights(
            source='SFO',
            destination='JFK',
            travel_date='2025-07-20',
            adults=1,
            sort_func=self.flight_search.sort_by_departure_time
        )
        
        # Verify we have multiple results to sort
        self.assertGreater(len(results), 1, "Need multiple flights to test sorting")
        
        # Extract departure times and verify they're in ascending order
        departure_times = []
        for flight in results:
            try:
                departure_time = flight['itineraries'][0]['segments'][0]['departure']['at']
                departure_times.append(departure_time)
            except (KeyError, IndexError):
                self.fail("Flight is missing required departure time data")
        
        # Check if departure times are in non-decreasing order
        for i in range(len(departure_times) - 1):
            self.assertLessEqual(departure_times[i], departure_times[i + 1],
                              f"Flights not sorted by departure time. {departure_times[i]} > {departure_times[i+1]}")
    
    def test_sort_by_arrival_time(self):
        """Test that flights are correctly sorted by arrival time (earliest first)."""
        # Get results sorted by arrival time
        results = self.flight_search.search_flights(
            source='SFO',
            destination='JFK',
            travel_date='2025-07-20',
            adults=1,
            sort_func=self.flight_search.sort_by_arrival_time
        )
        
        # Verify we have multiple results to sort
        self.assertGreater(len(results), 1, "Need multiple flights to test sorting")
        
        # Extract arrival times and verify they're in ascending order
        arrival_times = []
        for flight in results:
            try:
                segments = flight['itineraries'][0]['segments']
                arrival_time = segments[-1]['arrival']['at']
                arrival_times.append(arrival_time)
            except (KeyError, IndexError):
                self.fail("Flight is missing required arrival time data")
        
        # Check if arrival times are in non-decreasing order
        for i in range(len(arrival_times) - 1):
            self.assertLessEqual(arrival_times[i], arrival_times[i + 1],
                              f"Flights not sorted by arrival time. {arrival_times[i]} > {arrival_times[i+1]}")


if __name__ == '__main__':
    unittest.main()
