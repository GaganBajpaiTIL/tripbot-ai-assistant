import os
import logging.config
import json
from pathlib import Path

# Ensure logs directory exists
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Logging configuration
def setup_logging(default_level=logging.INFO):
    """Setup logging configuration"""
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "standard",
                "stream": "ext://sys.stderr"
            }
        },
        "loggers": {
            "tripbot": {
                "handlers": ["stdout", "stderr"],
                "level": "DEBUG",
                "propagate": False
            },
            "mcp": {
                "handlers": ["stdout", "stderr"],
                "level": "DEBUG",
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["stdout", "stderr"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["stdout", "stderr"],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["stdout", "stderr"],
                "propagate": False
            },
            "httpx": {
                "level": "WARNING",
                "handlers": ["stdout", "stderr"],
                "propagate": False
            },
            "httpcore": {
                "level": "WARNING",
                "handlers": ["stdout", "stderr"],
                "propagate": False
            }
        },
        "root": {
            "handlers": ["stdout", "stderr"],
            "level": "INFO"
        }
    }

    # Apply the configuration
    logging.config.dictConfig(log_config)
    
    # Set log level based on environment
    if os.getenv("ENVIRONMENT") != "PRODUCTION":
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("tripbot").setLevel(logging.DEBUG)
        logging.getLogger("mcp").setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger("tripbot").setLevel(logging.INFO)
        logging.getLogger("mcp").setLevel(logging.INFO)

# Call setup_logging when this module is imported
setup_logging()
