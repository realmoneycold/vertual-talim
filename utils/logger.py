import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logger():
    """Sets up standard output logging and error file logging."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clean existing handlers
    if logger.handlers:
        logger.handlers.clear()

    log_format = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] - %(message)s"
    )

    # Console output handler
    console_handler = sys.stdout
    stdout_handler = logging.StreamHandler(console_handler)
    stdout_handler.setFormatter(log_format)
    logger.addHandler(stdout_handler)

    # File output handler (creates a rotating file of max 5MB, keeping 3 backups)
    try:
        file_handler = RotatingFileHandler(
            "bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(log_format)
        file_handler.setLevel(logging.WARNING) # Log warnings and errors to file
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create RotatingFileHandler for bot.log: {e}")
