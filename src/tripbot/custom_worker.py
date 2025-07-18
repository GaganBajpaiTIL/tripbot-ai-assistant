import os
import sys
import signal
import traceback
import logging
from gunicorn.workers.gthread import ThreadWorker

logger = logging.getLogger(__name__)

class SegfaultHandlerWorker(ThreadWorker):
    """Custom worker that handles SIGSEGV and logs detailed information"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Register signal handlers
        signal.signal(signal.SIGSEGV, self.handle_segfault)
        signal.signal(signal.SIGABRT, self.handle_segfault)
    
    def handle_segfault(self, signum, frame):
        """Handle segmentation faults and log detailed information"""
        # Get the current exception information
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        # Log the signal information
        signal_name = 'SIGSEGV' if signum == signal.SIGSEGV else 'SIGABRT'
        logger.critical(
            f"{signal_name} detected in worker (pid: {os.getpid()})\n"
            f"Current frame: {frame}\n"
            f"Exception: {exc_type.__name__ if exc_type else 'None'}: {exc_value}\n"
            f"Traceback:\n{''.join(traceback.format_stack(frame))}"
        )
        
        # Write to stderr for additional visibility
        sys.stderr.write(
            f"\n!!! CRITICAL: {signal_name} in worker (pid: {os.getpid()}) !!!\n"
            f"!!! Please check the logs for detailed information !!!\n\n"
        )
        
        # Flush all log handlers
        for handler in logging.root.handlers:
            handler.flush()
        
        # Re-raise to allow Gunicorn to handle the worker restart
        os.kill(os.getpid(), signum)
    
    def run(self):
        """Override run method to add additional error handling"""
        try:
            return super().run()
        except MemoryError:
            logger.critical("Out of memory error in worker")
            raise
        except Exception as e:
            logger.exception("Unhandled exception in worker")
            raise
