import os
import sys
import signal
import traceback
import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

def install_signal_handlers():
    """Install signal handlers for critical errors"""
    def signal_handler(signum: int, frame: Any) -> None:
        """Handle segmentation faults and log detailed information"""
        signal_name = signal.Signals(signum).name
        
        # Get the current exception information if available
        exc_info = sys.exc_info()
        exc_type = exc_info[0].__name__ if exc_info[0] else 'None'
        exc_value = str(exc_info[1]) if exc_info[1] else 'No exception value'
        
        # Log the crash information
        logger.critical(
            f"!!! CRITICAL: {signal_name} in process {os.getpid()} !!!\n"
            f"Exception: {exc_type}: {exc_value}\n"
            f"Python traceback (if available):\n{''.join(traceback.format_stack(frame))}"
        )
        
        # Write to stderr for additional visibility
        sys.stderr.write(
            f"\n!!! CRITICAL: {signal_name} in process {os.getpid()} !!!\n"
            f"!!! Check logs for detailed information !!!\n\n"
        )
        
        # Flush all log handlers
        for handler in logging.root.handlers:
            handler.flush()
        
        # Re-raise the signal to allow default handler to run
        if signum == signal.SIGSEGV:
            # For SIGSEGV, we want to get a core dump if possible
            import faulthandler
            faulthandler.dump_traceback()
            os.abort()
        else:
            # For other signals, use the default handler
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)
    
    # Register signal handlers
    signal.signal(signal.SIGSEGV, signal_handler)  # Segmentation fault
    signal.signal(signal.SIGABRT, signal_handler)  # Abort signal
    signal.signal(signal.SIGFPE, signal_handler)   # Floating point exception
    signal.signal(signal.SIGILL, signal_handler)   # Illegal instruction
    signal.signal(signal.SIGBUS, signal_handler)   # Bus error
    
    logger.info(f"Installed signal handlers in process {os.getpid()}")

# Install signal handlers when this module is imported
#install_signal_handlers()
