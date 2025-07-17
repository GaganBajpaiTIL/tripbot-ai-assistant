import os
import sys
from pathlib import Path

# Add the src directory to Python path
project_root = os.path.dirname(__file__)
src_path = os.path.join(project_root, 'src')
package_path = os.path.join(src_path,"tripbot")

if src_path not in sys.path:
    sys.path.insert(0, src_path)
if package_path not in sys.path:
    sys.path.insert(0, package_path)

# Import after setting up path
from tripbot.config.logging_config import setup_logging
import logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

from app import app

if __name__ == '__main__':
    import uvicorn
    logger.info("Starting TripBot application...")
    uvicorn.run(
        "tripbot.app:app",
        host='0.0.0.0',
        port=50001,
        reload=True,
        log_config=None  # Disable uvicorn's default logging
    )

