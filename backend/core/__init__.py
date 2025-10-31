"""
Core module for AI Query Analyzer.

Provides configuration, logging, and shared utilities.
"""
from backend.core.config import settings, get_settings, DatabaseConfig
from backend.core.logger import get_logger, setup_logging

__all__ = [
    "settings",
    "get_settings",
    "DatabaseConfig",
    "get_logger",
    "setup_logging",
]
