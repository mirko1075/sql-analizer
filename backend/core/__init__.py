"""
Core module for AI Query Analyzer.

Provides configuration, logging, and shared utilities.
"""
from core.config import settings
from core.logger import setup_logger

__all__ = [
    "settings",
    "setup_logger",
]
