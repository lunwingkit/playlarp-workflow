import logging
import os
from datetime import datetime

# Define log levels mapped to Python's logging levels
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,     # Detailed troubleshooting (DEBUG and above)
    'INFO': logging.INFO,       # General progress (INFO and above)
    'WARNING': logging.WARNING, # Warnings and above
    'ERROR': logging.ERROR,     # Errors and critical only
    'CRITICAL': logging.CRITICAL # Critical only
}

def setup_logger(log_level='INFO', log_folder='log'):
    """Set up the logger with the specified log level and folder."""
    # Create log folder if it doesn't exist
    os.makedirs(log_folder, exist_ok=True)
    
    # Generate a timestamped log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_folder, f"app_log_{timestamp}.txt")
    
    # Configure logging for the root logger
    logging.basicConfig(
        filename=log_file,
        level=LOG_LEVELS.get(log_level, logging.INFO),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Add console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVELS.get(log_level, logging.INFO))
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(console_handler)
    
    # Suppress urllib3 debug logs unless explicitly enabled
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return log_file