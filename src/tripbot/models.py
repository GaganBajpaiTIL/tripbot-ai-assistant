from tripbot.database import Base
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON
from datetime import datetime,timezone

class TripBooking(Base):
    """Model for storing trip bookings"""
    __tablename__ = 'trip_bookings'
    id = Column(Integer, primary_key=True)
    traveler_name = Column(String(100), nullable=False)
    traveler_email = Column(String(120), nullable=False)
    destination = Column(String(200), nullable=False)
    departure_location = Column(String(200), nullable=False)
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    travelers_count = Column(Integer, default=1)
    trip_type = Column(String(50), default="round_trip")  # round_trip, one_way
    budget = Column(Float, nullable=True)
    preferences = Column(JSON, nullable=True)  # Store additional preferences as JSON
    booking_status = Column(String(50), default="confirmed")
    total_amount = Column(Float, nullable=True)
    payment_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

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

class ChatSession(Base):
    """Model for storing chat sessions and conversation state"""
    __tablename__ = 'chat_sessions'
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)
    conversation_state = Column(JSON, nullable=True)  # Store conversation state as JSON
    current_step = Column(String(50), default="greeting")
    collected_data = Column(JSON, nullable=True)  # Store collected trip data
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

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

