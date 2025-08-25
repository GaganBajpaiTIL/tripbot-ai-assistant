import os
import sys
import signal
from pathlib import Path
from signal import SIGINT, SIGTERM
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import async_sessionmaker
from pydantic import BaseModel
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import and configure logging
from tripbot.config.logging_config import setup_logging
import logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Import database configuration
from tripbot.database import Base, engine, SessionLocal, get_db

# Signal handlers
def handle_shutdown(signum, frame):
    logger.info('Shutting down gracefully...')
    sys.exit(0)

signal.signal(SIGINT, handle_shutdown)
signal.signal(SIGTERM, handle_shutdown)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the application.
    - Initializes the database on startup.
    - Disposes of the database connection on shutdown.
    """
    # Startup: Initialize database
    # Import models here to avoid circular imports
    from tripbot.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
    yield
    # Shutdown: Dispose of the database connection
    await engine.dispose()
    logger.info("Database connection closed")

app = FastAPI(title="TripBot AI Assistant", version="0.1.0", lifespan=lifespan)
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(project_root, "static")
os.makedirs(static_dir, exist_ok=True)  # Ensure the directory exists
# Log mount locations and static files
logger.info(f"Mount locations:")
logger.info(f"- /static -> {static_dir}")
staticFiles = StaticFiles(directory=static_dir)
app.mount("/static", staticFiles, name="static")
logger.info("Static files mounted")
logger.info(f"Mounted list {app.routes}")
# Add static files route for development
@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    static_file = os.path.join(static_dir, file_path)
    if os.path.isfile(static_file):
        return FileResponse(static_file)
    raise HTTPException(status_code=404, detail="File not found")

# Import routes
from tripbot.routes import router
from tripbot.travel_router import travel_router

# Include routes
app.include_router(router)
app.include_router(travel_router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("tripbot.app:app", host='0.0.0.0', port=50001, reload=True)
