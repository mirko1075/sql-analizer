"""
Logging configuration for the AI Query Analyzer backend.

Provides structured logging with configurable log levels and formats.
"""
import os
import sys
import logging
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log levels for better readability
    in terminal output.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname:8s}{self.RESET}"
            )
        return super().format(record)


def get_log_level() -> int:
    """
    Get log level from environment variable.

    Returns:
        Logging level (default: INFO)
    """
    level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
    return getattr(logging, level_name, logging.INFO)


def setup_logging():
    """
    Configure root logger with appropriate handlers and formatters.

    Should be called once at application startup.
    """
    log_level = get_log_level()
    env = os.getenv('ENV', 'development')

    # Create formatters
    if env == 'production':
        # JSON-like format for production (easier to parse by log aggregators)
        formatter = logging.Formatter(
            '{"time":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", '
            '"message":"%(message)s", "file":"%(filename)s", "line":%(lineno)d}'
        )
    else:
        # Human-readable format for development
        formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    root_logger.info(f"Logging initialized at {logging.getLevelName(log_level)} level")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name or __name__)


# Setup logging when module is imported
if not logging.getLogger().handlers:
    setup_logging()
