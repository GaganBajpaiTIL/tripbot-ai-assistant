import uuid
import json
import logging
from flask import render_template, request, jsonify, session
from app import app, db
from models import ChatSession
from llm_adapters import TripPlannerBot
from booking_service import BookingService

logger = logging.getLogger(__name__)

# Initialize services
trip_bot = TripPlannerBot(preferred_llm="bedrock")  # Can be changed to "gemini" or "bedrock"
booking_service = BookingService()

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Get or create session
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        # Get or create chat session
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            chat_session = ChatSession(
                session_id=session_id,
                conversation_state={'messages': []},
                current_step='greeting',
                collected_data={}
            )
            db.session.add(chat_session)
            db.session.commit()
        
        # Get conversation history
        conversation_history = chat_session.conversation_state.get('messages', [])
        
        # Generate bot response
        bot_response, next_step = trip_bot.generate_response(
            user_message,
            conversation_history,
            chat_session.current_step,
            chat_session.collected_data or {}
        )
        
        # Extract and store relevant data from user message
        updated_data = extract_data_from_message(
            user_message, 
            chat_session.current_step, 
            chat_session.collected_data or {}
        )
        
        # Update conversation history
        conversation_history.append({'role': 'user', 'content': user_message})
        conversation_history.append({'role': 'assistant', 'content': bot_response})
        
        # Update chat session
        chat_session.conversation_state = {'messages': conversation_history}
        chat_session.current_step = next_step
        chat_session.collected_data = updated_data
        db.session.commit()
        
        # Handle booking and payment steps
        additional_data = {}
        if next_step == 'booking_confirmation':
            # Calculate trip cost
            cost_breakdown = booking_service.calculate_trip_cost(updated_data)
            additional_data['cost_breakdown'] = cost_breakdown
        elif next_step == 'final_confirmation':
            # Create booking and process payment
            booking = booking_service.create_booking(updated_data)
            if booking:
                payment_result = booking_service.process_payment(booking.id, {})
                additional_data['booking'] = booking.to_dict()
                additional_data['payment'] = payment_result
        
        return jsonify({
            'response': bot_response,
            'current_step': next_step,
            'collected_data': updated_data,
            'additional_data': additional_data
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({'error': 'An error occurred processing your message'}), 500

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    """Get user's booking history"""
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({'error': 'Email parameter required'}), 400
        
        bookings = booking_service.get_bookings_by_email(email)
        return jsonify([booking.to_dict() for booking in bookings])
        
    except Exception as e:
        logger.error(f"Error fetching bookings: {e}")
        return jsonify({'error': 'Failed to fetch bookings'}), 500

@app.route('/api/booking/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    """Get specific booking details"""
    try:
        booking = booking_service.get_booking_by_id(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        return jsonify(booking.to_dict())
        
    except Exception as e:
        logger.error(f"Error fetching booking: {e}")
        return jsonify({'error': 'Failed to fetch booking'}), 500

@app.route('/api/booking/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    """Cancel a booking"""
    try:
        result = booking_service.cancel_booking(booking_id)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error cancelling booking: {e}")
        return jsonify({'error': 'Failed to cancel booking'}), 500

@app.route('/api/reset', methods=['POST'])
def reset_session():
    """Reset chat session"""
    try:
        session_id = session.get('session_id')
        if session_id:
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            if chat_session:
                db.session.delete(chat_session)
                db.session.commit()
        
        session.clear()
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error resetting session: {e}")
        return jsonify({'error': 'Failed to reset session'}), 500

def extract_data_from_message(message: str, current_step: str, existing_data: dict) -> dict:
    """Extract relevant data from user message based on current step"""
    data = existing_data.copy()
    message_lower = message.lower().strip()
    
    try:
        if current_step == 'name_collection' and not data.get('traveler_name'):
            # Extract name (simple approach - take the message as name)
            data['traveler_name'] = message.strip()
        
        elif current_step == 'email_collection' and '@' in message:
            # Extract email
            words = message.split()
            for word in words:
                if '@' in word and '.' in word:
                    data['traveler_email'] = word.strip()
                    break
        
        elif current_step == 'destination_collection' and not data.get('destination'):
            data['destination'] = message.strip()
        
        elif current_step == 'departure_location_collection' and not data.get('departure_location'):
            data['departure_location'] = message.strip()
        
        elif current_step == 'date_collection':
            # TODO: Add sophisticated date parsing.
            if 'departure_date' not in data:
                data['departure_date'] = message.strip()
            elif 'return_date' not in data:
                data['return_date'] = message.strip()
        
        elif current_step == 'travelers_count_collection':
            # Extract number
            import re
            numbers = re.findall(r'\d+', message)
            if numbers:
                data['travelers_count'] = numbers[0]
        
        elif current_step == 'trip_type_collection':
            if any(word in message_lower for word in ['round', 'return', 'back']):
                data['trip_type'] = 'round_trip'
            elif any(word in message_lower for word in ['one', 'single']):
                data['trip_type'] = 'one_way'
            else:
                data['trip_type'] = 'round_trip'  # Default
        
        elif current_step == 'budget_collection':
            # Extract budget
            import re
            amounts = re.findall(r'[\$]?(\d+)', message)
            if amounts:
                data['budget'] = amounts[0]
        
        elif current_step == 'preferences_collection':
            if not data.get('preferences'):
                data['preferences'] = {}
            data['preferences']['user_input'] = message.strip()
    
    except Exception as e:
        logger.error(f"Error extracting data from message: {e}")
    
    return data

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
