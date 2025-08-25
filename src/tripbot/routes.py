import uuid
from pathlib import Path
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select

# Import logging configuration
from tripbot.config.logging_config import setup_logging
import logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Local imports
from database import get_db
from models import ChatSession
from llm_adapters import BOT_TEXT_RESPONSE_KEY, QUESTION_KEY, USER_DATA_KEY,TOOL_CALL_KEY,TOOL_PARAMETERS_KEY
from trip_planner_bot import TripPlannerBot
from mcp_travel.flight_search_mcp import FlightSearchMCP
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
    response = templates.TemplateResponse(
        request=request,
        name="index.html"
    )
 
    return response

@router.get('/templates/flight_search_widget.html')
async def flight_search_widget(request: Request):
    return templates.TemplateResponse(request,"flight_search_widget.html")

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
        
    # Query the session by session_id (which is not the primary key)
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    chat_session = result.scalar_one_or_none()
    #TODO: Set up observer on collected_data
    if not chat_session:
        logger.info(f"Creating new chat session for session ID: {session_id}")
        chat_session = ChatSession(
            session_id=session_id,
            conversation_state={"messages": []},
            current_step='greeting',
              collected_data = {
                'timestamp': datetime.now().isoformat(),
                'traveler_name': "",
                'email': "",
                'destination': "",
                'departure_location': "",
                'departure_date': "",
                'return_date':"",
                'travelers_count': "",
                'trip_type': "",
                'budget': "",
                'preferences': {}
            }
        )
        db.add(chat_session)
        await db.commit()
        await db.refresh(chat_session)
        
    # Get conversation history
    conversation_history = chat_session.conversation_state.get('messages', [])
    if(conversation_history):
        conversation_history = json.loads(conversation_history)
    # Generate bot response
    bot_response, next_step, collected_data =  trip_bot.generate_response(
        user_message,
        conversation_history,
        chat_session.current_step,
        json.loads(chat_session.collected_data) if chat_session.collected_data else {}
    )
        
    # Extract and store relevant data from user message
    updated_data = extract_data_from_message(
        user_message, 
        chat_session.current_step, 
        collected_data
    )
        
        
    # Update conversation history
    conversation_history.append({'role': 'user', 'content': user_message})
    conversation_history.append({'role': 'assistant', 'content': bot_response})
        
    # Update chat session
    chat_session.conversation_state = {'messages': json.dumps(conversation_history)}
    chat_session.current_step = next_step
    chat_session.collected_data = json.dumps(collected_data)
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
    
    # Check if we should trigger flight search
    tool_call = bot_response.get(TOOL_CALL_KEY, "")
    if ('search' in tool_call and 'flight' in tool_call) or 'search_flight' in tool_call:
        if(validate_flight_search_parameters(updated_data)):
            tool_call = "search_flight"
        else:
            tool_call = "collect_flight_search_parameters"  
    response_data = {
        'response': bot_response.get(BOT_TEXT_RESPONSE_KEY, ""),
        'current_step': next_step,
        'collected_data': collected_data,
        'additional_data': additional_data,
        'tool_call': tool_call,
        'tool_parameters': bot_response.get(TOOL_PARAMETERS_KEY, {})
    }
    
    # Only add question if it exists in bot_response
    if QUESTION_KEY in bot_response:
        response_data[QUESTION_KEY] = bot_response[QUESTION_KEY]
        
    #Create JSONResponse with the session ID in headers
    response = JSONResponse(content=response_data)
    response.headers['x-session-id'] = session_id
    
    return response
        
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

def validate_flight_search_parameters(collected_data: dict) -> bool:
    """
    Validate if all required flight search parameters are present in the collected data.
    
    Args:
        collected_data: Dictionary containing collected user data
        
    Returns:
        bool: True if all required parameters are present and valid, False otherwise
    """
    required_fields = {
        'destination': str,
        'departure_location': str,
        'departure_date': str
    }
    
    # Check if all required fields are present and non-empty
    for field, field_type in required_fields.items():
        value = collected_data.get(field)
        if not value or not str(value).strip():
            return False
            
    # Validate travel dates format (YYYY-MM-DD or YYYY-MM-DD to YYYY-MM-DD)
    travel_dates = collected_data['departure_date'].strip()
    date_parts = travel_dates.split(' to ')
    
    if len(date_parts) == 1:  # Single date
        try:
            datetime.strptime(date_parts[0], '%Y-%m-%d')
        except ValueError:
            return False
    elif len(date_parts) == 2:  # Date range
        try:
            datetime.strptime(date_parts[0].strip(), '%Y-%m-%d')
            datetime.strptime(date_parts[1].strip(), '%Y-%m-%d')
        except (ValueError, IndexError):
            return False
    else:
        return False
        
    return True