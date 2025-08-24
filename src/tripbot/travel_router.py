from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database import get_db
from models import Booking
from mcp_travel.flight_search_mcp import FlightSearchMCP
# Initialize router
travel_router = APIRouter(prefix="/api/travel", tags=["travel"])

# Configure logging
logger = logging.getLogger(__name__)

@travel_router.get('/search_flights')
async def search_flights(
    request: Request,
    source: str = Query(..., description="Origin airport or city code"),
    destination: str = Query(..., description="Destination airport or city code"),
    travel_date: str = Query(..., description="Departure date in YYYY-MM-DD format"),
    return_date: Optional[str] = Query(None, description="Return date in YYYY-MM-DD format (optional)"),
    adults: int = Query(1, ge=1, le=9, description="Number of adult passengers"),
    children: int = Query(0, ge=0, le=8, description="Number of child passengers"),
    infants: int = Query(0, ge=0, le=5, description="Number of infant passengers"),
    travel_class: str = Query("ECONOMY", description="Travel class (e.g., ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)")
):
    """
    Search for flights between two locations on specific dates.
    
    Returns a list of available flights with pricing and itinerary information.
    """
    try:
        # Initialize the flight search client
        flight_search = FlightSearchMCP()
        
        # Call the search_flights method with the provided parameters
        flights = flight_search.search_flights(
            source=source.upper(),
            destination=destination.upper(),
            travel_date=travel_date,
            return_date=return_date,
            adults=adults,
            children=children,
            infants=infants,
            travel_class=travel_class.upper(),
            max_results=10  # Limit to 10 results by default
        )
        
        return JSONResponse({
            "status": "success",
            "data": flights,
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

@travel_router.get('/bookings')
async def get_bookings(db: AsyncSession = Depends(get_db)):
    """Get user's booking history"""
    try:
        # In a real app, you would filter by the current user
        result = await db.execute("""
            SELECT * FROM bookings
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
            "SELECT * FROM bookings WHERE id = :booking_id",
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
            "UPDATE bookings SET status = 'cancelled' WHERE id = :booking_id RETURNING *",
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
