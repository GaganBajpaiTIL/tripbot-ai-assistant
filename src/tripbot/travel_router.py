from typing import Optional, Any
import json
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request, HTTPException, Query,Form,Body 
from fastapi.responses import JSONResponse
from urllib.parse import unquote
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from models import TripBooking
from database import get_db
from mcp_travel.flight_search_mcp import FlightSearchMCP
# Initialize router
travel_router = APIRouter(prefix="/api/travel", tags=["travel"])
class Flight_Search_Req(BaseModel):
    origin :str
    destination :str
    departure_date:str
    return_date: Optional[str] =Form(None)
    passengers:int
    # # children:Optional[int] = Form(None)
    # # infants:Optional[int] = Form(None)
    travel_class:Optional[str] =Form("ECONOMY")

class FlightBookingRequest(BaseModel):
    user_email: str
    user_name: str
    flight_raw_data: str
    passengers: list[dict]

# Configure logging
logger = logging.getLogger(__name__)

@travel_router.post('/search_flights')
async def search_flights(
    request: Request,
    flight_search: Flight_Search_Req = Body()

):
    """
    Search for flights between two locations on specific dates.
    """
    try:
        # Extract parameters from the request body
        # source = flight_search.get('origin')
        # destination = flight_search.get('destination')
        # travel_date = flight_search.get('departure_date')
        # return_date = flight_search.get('return_date')
        # adults = flight_search.get('adults', 1)
        # children = flight_search.get('children', 0)
        # infants = flight_search.get('infants', 0)
        # travel_class = flight_search.get('travel_class', 'ECONOMY')

        source = flight_search.origin
        destination = flight_search.destination
        travel_date = flight_search.departure_date
        return_date = flight_search.return_date
        adults = flight_search.passengers
        children = 0 # flight_search.children if flight_search.children else 0
        infants = 0 #flight_search.infants if flight_search.infants else 0
        travel_class = flight_search.travel_class if flight_search.travel_class else "ECONOMY"

        
        # Initialize the flight search client
        flight_search_mcp = FlightSearchMCP()
        source_IATA_codes = flight_search_mcp.get_iata_code(source, "IN")
        soucrce_IATA = source_IATA_codes[0]['iataCode']
        destination_IATA_codes = flight_search_mcp.get_iata_code(destination,"IN")
        destination_IATA = destination_IATA_codes[0]['iataCode']
        
        # Call the search_flights method with the provided parameters
        flights = flight_search_mcp.search_flights(
            source=soucrce_IATA,
            destination=destination_IATA,
            travel_date=travel_date,
            return_date=return_date,
            adults=adults,
            children=children,
            infants=infants,
            travel_class=travel_class.upper(),
            non_stop=True,
            max_results=5  # Limit to 10 results by default
        )
        flight_results = getJSFormat(flights)
        return JSONResponse({
            "status": "success",
            "flights_results": flight_results,
            "message": f"Found {len(flights)} flights"
        })
        
    except ValueError as ve:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(ve)}
        )
    except Exception as e:
        logger.error(f"Error searching flights: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Failed to search for flights. Please try again later."}
        )
def getJSFormat(flights):
    """
    Convert flight data from the API format to the format expected by the frontend.
    
    Args:
        flights: List of flight objects from the flight search API
        
    Returns:
        List of flight objects in the frontend format
    """
    formatted_flights = []
    
    for flight in flights:
        # Extract the first segment (assuming non-stop flights)
        segment = flight['itineraries'][0]['segments'][0]
        
        # Parse the duration string (e.g., "PT2H30M") into minutes
        duration_str = flight['itineraries'][0]['duration']
        hours = 0
        minutes = 0
        if 'H' in duration_str:
            hours = int(duration_str.split('H')[0].split('T')[-1])
        if 'M' in duration_str:
            minutes = int(duration_str.split('H')[-1].split('M')[0])
        total_minutes = hours * 60 + minutes
        
        formatted_flight = {
            'id': flight['id'],
            'airline': segment.get('carrierCode', ''),
            'airline_name': segment.get('carrierCode', ''),  # Will be replaced with actual airline name if available
            'flight_number': segment.get('number', ''),
            'aircraft': segment.get('aircraft', {}).get('code', ''),
            'departure_airport': segment['departure']['iataCode'],
            'arrival_airport': segment['arrival']['iataCode'],
            'departure_time': segment['departure']['at'],
            'arrival_time': segment['arrival']['at'],
            'duration': total_minutes,
            'price': float(flight['price']['total']),
            'currency': flight['price']['currency'],
            'stops': len(flight['itineraries'][0]['segments']) - 1,
            'raw': json.dumps(flight)
        }

        # Try to get airline name from the operating carrier if available
        operating = segment.get('operating', {})
        if 'carrierCode' in operating:
            formatted_flight['airline_name'] = operating['carrierCode']
        
        formatted_flights.append(formatted_flight)
    
    return formatted_flights



@travel_router.get('/bookings')
async def get_bookings(db: AsyncSession = Depends(get_db)):
    """Get user's booking history"""
    try:
        # In a real app, you would filter by the current user
        result = await db.execute("""
            SELECT * FROM tripbooking
            ORDER BY created_at DESC
            LIMIT 100
        """)
        bookings = result.mappings().all()
        return {"status": "success", "data": bookings}
    except Exception as e:
        logger.error(f"Error fetching bookings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch bookings")

@travel_router.get('/bookings/{booking_id}')
async def get_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    """Get specific booking details"""
    try:
        result = await db.execute(
            "SELECT * FROM tripbooking WHERE id = :booking_id",
            {"booking_id": booking_id}
        )
        booking = result.mappings().first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        return {"status": "success", "data": booking}
    except Exception as e:
        logger.error(f"Error fetching booking {booking_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch booking")

@travel_router.delete('/bookings/{booking_id}')
async def cancel_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    """Cancel a booking"""
    try:
        # In a real app, you would verify the user owns this booking
        result = await db.execute(
            "UPDATE tripbooking SET booking_status = 'cancelled' WHERE id = :booking_id RETURNING *",
            {"booking_id": booking_id}
        )
        booking = result.mappings().first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        await db.commit()
        return {"status": "success", "message": "Booking cancelled"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error cancelling booking {booking_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel booking")

@travel_router.post('/book_flight')
async def book_flight(
    booking_request: FlightBookingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Book a flight with the provided user details and flight data.
    Returns PNR and itinerary details.
    """
    try:
        # Create a new booking record in the database
        # new_booking = TripBooking(
        #     traveler_email=booking_request.user_email,
        #     traveler_name=booking_request.user_name,
        #     booking_status="CONFIRMED"
        # )
        
        # db.add(new_booking)
        # await db.commit()
        # await db.refresh(new_booking)
        
        # Generate a mock PNR (in a real app, this would come from the airline's API)
        import random
        import string
        pnr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        flight_data= (json.loads(unquote(booking_request.flight_raw_data)) if booking_request.flight_raw_data else None ) ,
        passengers=json.dumps(booking_request.passengers),
        # Prepare response with booking details
        response = {
            "status": "success",
            "booking_id": "",
            "pnr": pnr,
            "itinerary": {
                "user": {
                    "name": booking_request.user_name,
                    "email": booking_request.user_email
                },
                "flight_details": flight_data,
                "passengers": passengers,
                "booking_status": "CONFIRMED"
            }
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        logger.error(f"Error booking flight: {str(e)}", exc_info=True)
        await db.rollback()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Failed to process booking. Please try again."}
        )
