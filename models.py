from app import db
from datetime import datetime
from sqlalchemy import JSON

class TripBooking(db.Model):
    """Model for storing trip bookings"""
    id = db.Column(db.Integer, primary_key=True)
    traveler_name = db.Column(db.String(100), nullable=False)
    traveler_email = db.Column(db.String(120), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    departure_location = db.Column(db.String(200), nullable=False)
    departure_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=True)
    travelers_count = db.Column(db.Integer, default=1)
    trip_type = db.Column(db.String(50), default="round_trip")  # round_trip, one_way
    budget = db.Column(db.Float, nullable=True)
    preferences = db.Column(JSON, nullable=True)  # Store additional preferences as JSON
    booking_status = db.Column(db.String(50), default="confirmed")
    total_amount = db.Column(db.Float, nullable=True)
    payment_status = db.Column(db.String(50), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert booking to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'traveler_name': self.traveler_name,
            'traveler_email': self.traveler_email,
            'destination': self.destination,
            'departure_location': self.departure_location,
            'departure_date': self.departure_date.isoformat() if self.departure_date else None,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'travelers_count': self.travelers_count,
            'trip_type': self.trip_type,
            'budget': self.budget,
            'preferences': self.preferences,
            'booking_status': self.booking_status,
            'total_amount': self.total_amount,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ChatSession(db.Model):
    """Model for storing chat sessions and conversation state"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    conversation_state = db.Column(JSON, nullable=True)  # Store conversation state as JSON
    current_step = db.Column(db.String(50), default="greeting")
    collected_data = db.Column(JSON, nullable=True)  # Store collected trip data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert session to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'conversation_state': self.conversation_state,
            'current_step': self.current_step,
            'collected_data': self.collected_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

