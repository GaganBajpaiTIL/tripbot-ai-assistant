import os
import sys
import signal
from pathlib import Path
from signal import SIGINT, SIGTERM

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import async_sessionmaker
from pydantic import BaseModel

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
from database import Base, engine, SessionLocal, get_db

# Signal handlers
def handle_shutdown(signum, frame):
    logger.info('Shutting down gracefully...')
    sys.exit(0)

signal.signal(SIGINT, handle_shutdown)
signal.signal(SIGTERM, handle_shutdown)

app = FastAPI(title="TripBot AI Assistant", version="0.1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    # Import models here to avoid circular imports
    from models import Base
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

@app.on_event("shutdown")
async def shutdown_event():
    await engine.dispose()
    logger.info("Database connection closed")

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
from routes import router

# Include routes
app.include_router(router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("tripbot.app:app", host='0.0.0.0', port=50001, reload=True)

