"""
Database layer package.

Contains SQLAlchemy models, session management, and database utilities.
"""

from backend.db.models import (
    Base,
    SlowQueryRaw,
    AnalysisResult,
    DbMetadata,
    OptimizationHistory,
    SchemaVersion,
)
from backend.db.session import (
    get_db,
    get_db_context,
    check_db_connection,
    init_db,
    close_db_connections,
)

__all__ = [
    # Models
    "Base",
    "SlowQueryRaw",
    "AnalysisResult",
    "DbMetadata",
    "OptimizationHistory",
    "SchemaVersion",
    # Session
    "get_db",
    "get_db_context",
    "check_db_connection",
    "init_db",
    "close_db_connections",
]
