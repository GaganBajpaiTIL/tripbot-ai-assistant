import multiprocessing
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

# Logging configuration
loglevel = "info"
access_log_format = "%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\""

# Development settings
if os.environ.get("ENVIRONMENT") != "PRODUCTION":
    reload = True
    loglevel = "debug"
    accesslog = "-"
    errorlog = "-"

# Production settings
else:
    preload_app = True
    worker_class = "gthread"  # Use gthread worker for better performance
    workers = multiprocessing.cpu_count() * 1 + 1
    threads = 2
    max_requests = 1000
    max_requests_jitter = 50
    accesslog = "/app/log/gunicorn/access.log"
    errorlog = "/app/log/gunicorn/error.log"