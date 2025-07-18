import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from models import TripBooking
from database import SessionLocal
from mcp.flight_search_mcp import FlightSearchMCP

logger = logging.getLogger(__name__)

class BookingService:
    """Service for handling trip bookings and payments"""
    
    def __init__(self):
        self.mock_hotels = [
            {"name": "Grand Plaza Hotel", "rating": 4.5, "price_per_night": 150},
            {"name": "Comfort Inn & Suites", "rating": 4.0, "price_per_night": 120},
            {"name": "Luxury Resort & Spa", "rating": 5.0, "price_per_night": 300},
            {"name": "Budget Express Hotel", "rating": 3.5, "price_per_night": 80},
            {"name": "Boutique City Hotel", "rating": 4.2, "price_per_night": 200}
        ]
        
        self.mock_flights = [
            {"airline": "SkyLine Airways", "price": 450, "duration": "3h 45m"},
            {"airline": "Global Express", "price": 520, "duration": "4h 15m"},
            {"airline": "Budget Air", "price": 380, "duration": "5h 30m"},
            {"airline": "Premium Wings", "price": 680, "duration": "3h 20m"},
            {"airline": "Economy Plus", "price": 420, "duration": "4h 45m"}
        ]
        
        # Initialize FlightSearchMCP instance
        self.flight_search = FlightSearchMCP()
    
    def calculate_trip_cost(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate estimated trip cost based on collected data"""
        try:
            # Extract trip details
            departure_date = datetime.strptime(trip_data.get('departure_date', ''), '%Y-%m-%d')
            return_date_str = trip_data.get('return_date')
            travelers_count = int(trip_data.get('travelers_count', 1))
            
            # Calculate number of nights
            if return_date_str:
                return_date = datetime.strptime(return_date_str, '%Y-%m-%d')
                nights = (return_date - departure_date).days
            else:
                nights = 3  # Default for one-way trips
            
            # Select random hotel and flight for pricing
            hotel = random.choice(self.mock_hotels)
            flight = random.choice(self.mock_flights)
            
            # Calculate costs
            flight_cost = flight['price'] * travelers_count
            if trip_data.get('trip_type') == 'round_trip':
                flight_cost *= 2  # Round trip
            
            hotel_cost = hotel['price_per_night'] * nights * travelers_count
            
            # Add taxes and fees (15% of total)
            subtotal = flight_cost + hotel_cost
            taxes_and_fees = subtotal * 0.15
            total_cost = subtotal + taxes_and_fees
            
            return {
                'flight_details': flight,
                'hotel_details': hotel,
                'flight_cost': flight_cost,
                'hotel_cost': hotel_cost,
                'nights': nights,
                'subtotal': subtotal,
                'taxes_and_fees': taxes_and_fees,
                'total_cost': total_cost,
                'travelers_count': travelers_count
            }
            
        except Exception as e:
            logger.error(f"Error calculating trip cost: {e}")
            return {
                'error': 'Unable to calculate trip cost',
                'total_cost': 0
            }
    
    def search_flights(
        self,
        travel_date: str,
        source: str,
        destination: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        travel_class: str = 'ECONOMY',
        max_results: int = 5,
        include_business_class: bool = True,
        include_premium_economy: bool = True,
        non_stop: bool = False,
        max_price: Optional[float] = None,
        currency_code: str = "INR",
        sort_func: Optional[Callable[[Dict[str, Any]], Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for available flights between a source and destination on a given date.
        
        Args:
            travel_date: The desired date of travel in 'YYYY-MM-DD' format
            source: The departure airport code (e.g., 'SFO', 'LAX') or city name
            destination: The arrival airport code (e.g., 'JFK', 'LHR') or city name
            return_date: The desired date of return in 'YYYY-MM-DD' format (optional)
            adults: Number of adult passengers (1-9)
            children: Number of child passengers (0-8)
            infants: Number of infant passengers (0-5, cannot exceed number of adults)
            travel_class: Travel class ('ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST')
            max_results: Maximum number of results to return (1-10)
            include_business_class: Whether to include business class flights
            include_premium_economy: Whether to include premium economy flights
            non_stop: Whether to include only non-stop flights
            max_price: Maximum price for the flight (in the specified currency)
            currency_code: Currency code for pricing (3-letter ISO code, e.g., 'USD', 'EUR', 'INR')
            sort_func: Optional function to use for sorting results. If None, defaults to sorting by duration.
            
        Returns:
            List of flight options matching the search criteria
            
        Example:
            flights = booking_service.search_flights(
                travel_date="2025-08-15",
                source="SFO",
                destination="JFK",
                return_date="2025-08-22",
                adults=2,
                travel_class="ECONOMY"
            )
        """
        try:
            return self.flight_search.search_flights(
                travel_date=travel_date,
                return_date=return_date,
                source=source,
                destination=destination,
                adults=adults,
                children=children,
                infants=infants,
                travel_class=travel_class,
                max_results=max_results,
                include_business_class=include_business_class,
                include_premium_economy=include_premium_economy,
                non_stop=non_stop,
                max_price=max_price,
                currencyCode=currency_code,
                sort_func=sort_func
            )
        except Exception as e:
            logger.error(f"Error searching for flights: {e}")
            return []
    
    async def create_booking(self, trip_data: Dict[str, Any]) -> Optional[TripBooking]:
        """Create a new trip booking"""
        try:
            # Calculate trip cost
            cost_breakdown = self.calculate_trip_cost(trip_data)
            
            # Create booking record
            booking = TripBooking(
                traveler_name=trip_data.get('traveler_name', ''),
                traveler_email=trip_data.get('traveler_email', ''),
                destination=trip_data.get('destination', ''),
                departure_location=trip_data.get('departure_location', ''),
                departure_date=datetime.strptime(trip_data.get('departure_date', ''), '%Y-%m-%d').date(),
                return_date=datetime.strptime(trip_data.get('return_date', ''), '%Y-%m-%d').date() if trip_data.get('return_date') else None,
                travelers_count=int(trip_data.get('travelers_count', 1)),
                trip_type=trip_data.get('trip_type', 'round_trip'),
                budget=float(trip_data.get('budget', 0)) if trip_data.get('budget') else None,
                preferences=trip_data.get('preferences', {}),
                total_amount=cost_breakdown.get('total_cost', 0),
                booking_status='confirmed',
                payment_status='pending'
            )
            
            async with SessionLocal() as session:
                async with session.begin():
                    session.add(booking)
            
            logger.info(f"Created booking {booking.id} for {booking.traveler_email}")
            return booking
            
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            async with SessionLocal() as session:
                async with session.begin():
                    session.rollback()
            return None
    
    async def process_payment(self, booking_id: int, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment for a booking (mock implementation)"""
        try:
            booking = TripBooking.query.get(booking_id)
            if not booking:
                return {'success': False, 'error': 'Booking not found'}
            
            # Mock payment processing
            # In a real implementation, this would integrate with a payment gateway
            payment_success = random.choice([True, True, True, False])  # 75% success rate
            
            if payment_success:
                booking.payment_status = 'completed'
                booking.booking_status = 'confirmed'
                
                # Generate mock confirmation details
                confirmation_number = f"TRP{random.randint(100000, 999999)}"
                
                async with SessionLocal() as session:
                    async with session.begin():
                        session.commit()
                
                return {
                    'success': True,
                    'confirmation_number': confirmation_number,
                    'amount_charged': booking.total_amount,
                    'booking_id': booking.id
                }
            else:
                return {
                    'success': False,
                    'error': 'Payment processing failed. Please check your payment details and try again.'
                }
                
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return {'success': False, 'error': 'Payment processing error'}
    
    def get_booking_by_id(self, booking_id: int) -> Optional[TripBooking]:
        """Retrieve booking by ID"""
        return TripBooking.query.get(booking_id)
    
    def get_bookings_by_email(self, email: str) -> list:
        """Retrieve all bookings for an email address"""
        return TripBooking.query.filter_by(traveler_email=email).order_by(TripBooking.created_at.desc()).all()
    
    def cancel_booking(self, booking_id: int) -> Dict[str, Any]:
        """Cancel a booking"""
        try:
            booking = TripBooking.query.get(booking_id)
            if not booking:
                return {'success': False, 'error': 'Booking not found'}
            
            booking.booking_status = 'cancelled'
            db.session.commit()
            
            return {'success': True, 'message': 'Booking cancelled successfully'}
            
        except Exception as e:
            logger.error(f"Error cancelling booking: {e}")
            return {'success': False, 'error': 'Failed to cancel booking'}

