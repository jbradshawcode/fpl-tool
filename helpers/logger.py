import logging

def setup_logger():
    """Initialize logging configuration - call this once at app startup"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

def get_logger(name):
    """Get a logger instance for a specific module"""
    return logging.getLogger(name)
