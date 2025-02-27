# logging_config.py
import logging
import os
from datetime import datetime

# Define log levels mapped to Python's logging levels
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

def setup_logger(log_level='INFO', log_folder='log'):
    """Set up the logger with the specified log level and folder."""
    # Create log folder if it doesn't exist
    os.makedirs(log_folder, exist_ok=True)
    
    # Generate a timestamped log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_folder, f"app_log_{timestamp}.txt")
    
    # Configure logging for the root logger
    logger = logging.getLogger()
    logger.setLevel(LOG_LEVELS.get(log_level, logging.INFO))

    # File handler with no buffering
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(LOG_LEVELS.get(log_level, logging.INFO))
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    file_handler.flush = lambda: file_handler.stream.flush()  # Ensure immediate write
    
    # Console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVELS.get(log_level, logging.INFO))
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Clear existing handlers and add new ones
    logger.handlers = []
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Suppress urllib3 debug logs unless explicitly enabled
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return log_file