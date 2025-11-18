"""Compatibility package for database helpers.

This module provides a package path `backend.db` expected by the application
and re-exports session helpers implemented in this package.
"""

from .session import *  # noqa: F401,F403
