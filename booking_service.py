import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from models import TripBooking
from app import db

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
    
    def create_booking(self, trip_data: Dict[str, Any]) -> Optional[TripBooking]:
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
            
            db.session.add(booking)
            db.session.commit()
            
            logger.info(f"Created booking {booking.id} for {booking.traveler_email}")
            return booking
            
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            db.session.rollback()
            return None
    
    def process_payment(self, booking_id: int, payment_details: Dict[str, Any]) -> Dict[str, Any]:
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
                
                db.session.commit()
                
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

