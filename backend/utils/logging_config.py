"""
Centralized logging configuration for the backend.
"""
import logging
import sys


def setup_logging(level: str = "INFO"):
    """
    Configure logging for the entire application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress noisy third-party loggers
    _suppress_third_party_loggers()


def _suppress_third_party_loggers():
    """Suppress verbose output from third-party libraries"""
    noisy_loggers = [
        "requests",
        "urllib3",
        "openai",
        "httpcore",
        "httpx",
        "pydub",
        "elevenlabs",
        "langchain",
        "openai._base_client"
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Usually __name__ of the calling module
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
