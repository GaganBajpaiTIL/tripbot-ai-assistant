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



# Worker configuration
worker_class = 'gthread'  # Using gthread worker for better signal handling
workers = 2
threads = 2
timeout = 1200
keepalive = 2
preload_app = True  # Keep preload enabled to ensure signal handlers are installed early 

# Error handling
max_requests = 1000  # Restart workers after this many requests
max_requests_jitter = 50  # Add randomness to prevent all workers restarting at once

# Memory management
import resource

# Enable core dumps for debugging SIGSEGV
resource.setrlimit(resource.RLIMIT_CORE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))


# Logging configuration
loglevel = 'info'
accesslog = '-'
errorlog = '-'
capture_output = True
enable_stdio_inheritance = True  # Capture output from subprocesses



# Logging configuration
log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

# Log to stdout and stderr
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
capture_output = True

# Common logging configuration
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': log_format},
        'access': {'format': '%(message)s'}
    },
    'handlers': {
        #'error_file': {
        #    'class': 'logging.handlers.RotatingFileHandler',
        #    'filename': str(error_log),
        #    'maxBytes': max_size,
        #    'backupCount': backup_count,
        #    'formatter': 'standard'
        #},
        #'access_file': {
        #    'class': 'logging.handlers.RotatingFileHandler',
        #    'filename': str(access_log),
        #    'maxBytes': max_size,
        #    'backupCount': backup_count,
        #    'formatter': 'access'
        #},
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        }
    },
    'loggers': {
        'gunicorn.error': {
            'handlers': ['console'],
            'level': 'DEBUG' if os.environ.get("ENVIRONMENT") != "PRODUCTION" else 'INFO',
            'propagate': False
        },
        'gunicorn.access': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG' if os.environ.get("ENVIRONMENT") != "PRODUCTION" else 'INFO'
    }
}

# Common settings
loglevel = "debug" if os.environ.get("ENVIRONMENT") != "PRODUCTION" else "info"
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