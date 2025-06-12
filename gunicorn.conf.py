import os
import multiprocessing
import logging
from pathlib import Path
import os
import sys

# Add the src directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
src_path = os.path.join(project_root, 'src')
package_path = os.path.join(src_path,"tripbot")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if package_path not in sys.path:
    sys.path.insert(0, package_path)

# Server socket
bind = "0.0.0.0:50001"



# Worker processes
#workers = multiprocessing.cpu_count() * 1 + 1
workers = 2
threads = 2
timeout = 30
keepalive = 2
# Preloading as init seems to have a racing condition and db create.
preload_app = True



# Logging configuration
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Log file settings
max_size = 100 * 1024 * 1024  # 100MB
backup_count = 5
log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

# Set up log files
access_log = log_dir / "access.log"
error_log = log_dir / "error.log"

# Ensure log files exist
for log_file in [access_log, error_log]:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if not log_file.exists():
        log_file.touch()

# Common logging configuration
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': log_format},
        'access': {'format': '%(message)s'}
    },
    'handlers': {
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(error_log),
            'maxBytes': max_size,
            'backupCount': backup_count,
            'formatter': 'standard'
        },
        'access_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(access_log),
            'maxBytes': max_size,
            'backupCount': backup_count,
            'formatter': 'access'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        }
    },
    'loggers': {
        'gunicorn.error': {
            'handlers': ['error_file', 'console'],
            'level': 'DEBUG' if os.environ.get("ENVIRONMENT") != "PRODUCTION" else 'INFO',
            'propagate': False
        },
        'gunicorn.access': {
            'handlers': ['access_file'],
            'level': 'INFO',
            'propagate': False
        }
    },
    'root': {
        'handlers': ['error_file', 'console'],
        'level': 'DEBUG' if os.environ.get("ENVIRONMENT") != "PRODUCTION" else 'INFO'
    }
}

# Common settings
loglevel = "debug" if os.environ.get("ENVIRONMENT") != "PRODUCTION" else "info"
accesslog = str(access_log)
errorlog = str(error_log)
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Development settings
if os.environ.get("ENVIRONMENT") != "PRODUCTION":
    reload = True
    # In development, also log to console
    logconfig_dict['loggers']['gunicorn.error']['handlers'].append('console')

# Production settings
else:
    worker_class = "gthread"
    workers = multiprocessing.cpu_count() * 1 + 1
    threads = 2
    max_requests = 1000
    max_requests_jitter = 50