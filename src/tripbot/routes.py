import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

# Import logging configuration
from tripbot.config.logging_config import setup_logging
import logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Local imports
from database import get_db
from models import ChatSession
from llm_adapters import BOT_TEXT_RESPONSE_KEY, QUESTION_KEY, USER_DATA_KEY
from trip_planner_bot import TripPlannerBot
from booking_service import BookingService

router = APIRouter()

# Get the directory where this file is located
current_dir = Path(__file__).parent
templates = Jinja2Templates(directory=str(current_dir / ".." / ".." / "templates"))
# Initialize services
trip_bot = TripPlannerBot(preferred_llm="bedrock")  # Can be changed to "gemini" or "bedrock"
booking_service = BookingService()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    message: str
    step: str
    data: dict

@router.get('/')
async def index(request: Request):
    """Main chat interface"""
    response = templates.TemplateResponse("index.html", {"request": request})
    # Set session ID in response headers if not already present
    if not request.headers.get('x-session-id'):
        session_id = str(uuid.uuid4())
        response.headers['x-session-id'] = session_id
        logger.info(f"Set new session ID in response: {session_id}")
    return response

@router.post('/api/chat', response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle chat messages"""
    user_message = chat_request.message.strip()
    
    if not user_message:
        raise HTTPException(status_code=400, detail='Message cannot be empty')
        
    # Get or create session
    session_id = request.headers.get('x-session-id')  # Headers are case-insensitive
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session ID: {session_id}")
        
    # Get or create chat session
    chat_session = await db.get(ChatSession, session_id)
    if not chat_session:
        logger.info(f"Creating new chat session for session ID: {session_id}")
        chat_session = ChatSession(
            session_id=session_id,
            conversation_state={'messages': []},
            current_step='greeting',
            collected_data={}
        )
        db.add(chat_session)
        await db.commit()
        await db.refresh(chat_session)
        
    # Get conversation history
    conversation_history = chat_session.conversation_state.get('messages', [])

    # Generate bot response
    bot_response, next_step, collected_data =  trip_bot.generate_response(
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
    await db.commit()
    await db.refresh(chat_session)
        
    # Handle booking and payment steps
    additional_data = {}
    if next_step == 'booking_confirmation':
        # Calculate trip cost
        cost_breakdown = await booking_service.calculate_trip_cost(updated_data)
        additional_data['cost_breakdown'] = cost_breakdown
    elif next_step == 'final_confirmation':
        # Create booking and process payment
            booking = await booking_service.create_booking(updated_data)
            if booking:
                payment_result = await booking_service.process_payment(booking.id, {})
                additional_data['booking'] = booking.to_dict()
                additional_data['payment'] = payment_result
        
    response_data = {
        'response': bot_response.get(BOT_TEXT_RESPONSE_KEY, ""),
        'current_step': next_step,
        'collected_data': updated_data,
        'additional_data': additional_data
    }
    
    # Only add question if it exists in bot_response
    if QUESTION_KEY in bot_response:
        response_data[QUESTION_KEY] = bot_response[QUESTION_KEY]
        
    # Only add tool_call and tool_parameters if tool_call exists in bot_response
    if "tool_call" in bot_response:
        response_data['tool_call'] = bot_response["tool_call"]
        if "tool_parameters" in bot_response:
            response_data['tool_parameters'] = bot_response["tool_parameters"]
    
    return JSONResponse(response_data)
        

@router.get('/api/bookings')
async def get_bookings(db: AsyncSession = Depends(get_db)):
    """Get user's booking history"""
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({'error': 'Email parameter required'}), 400
        
        async with db.begin():
            bookings = await booking_service.get_bookings_by_email(email)
        return jsonify([booking.to_dict() for booking in bookings])
        
    except Exception as e:
        logger.error(f"Error fetching bookings: {e}")
        return jsonify({'error': 'Failed to fetch bookings'}), 500

@router.get('/api/booking/{booking_id}')
async def get_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    """Get specific booking details"""
    try:
        async with db.begin():
            booking = await booking_service.get_booking_by_id(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        return jsonify(booking.to_dict())
        
    except Exception as e:
        logger.error(f"Error fetching booking: {e}")
        return jsonify({'error': 'Failed to fetch booking'}), 500

@router.post('/api/booking/{booking_id}/cancel')
async def cancel_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    """Cancel a booking"""
    try:
        async with db.begin():
            result = await booking_service.cancel_booking(booking_id)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error cancelling booking: {e}")
        return jsonify({'error': 'Failed to cancel booking'}), 500

@router.post('/api/reset')
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

from fastapi import HTTPException, FastAPI

# Remove router-level exception handlers and handle errors directly in endpoints

@router.get('/api/bookings')
async def get_bookings(db: AsyncSession = Depends(get_db)):
    """Get user's booking history"""
    try:
        email = request.args.get('email')
        if not email:
            raise HTTPException(status_code=400, detail='Email parameter required')
        
        async with db.begin():
            bookings = await booking_service.get_bookings_by_email(email)
        return [booking.to_dict() for booking in bookings]
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching bookings: {e}")
        raise HTTPException(status_code=500, detail='Failed to fetch bookings')

@router.get('/api/booking/{booking_id}')
async def get_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    """Get specific booking details"""
    try:
        async with db.begin():
            booking = await booking_service.get_booking_by_id(booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail='Booking not found')
        
        return booking.to_dict()
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching booking: {e}")
        raise HTTPException(status_code=500, detail='Failed to fetch booking')

@router.post('/api/booking/{booking_id}/cancel')
async def cancel_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    """Cancel a booking"""
    try:
        async with db.begin():
            result = await booking_service.cancel_booking(booking_id)
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to cancel booking'))
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error cancelling booking: {e}")
        raise HTTPException(status_code=500, detail='Failed to cancel booking')
