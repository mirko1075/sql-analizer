"""Database session utilities for the backend package.

This is a minimal implementation used for local development and tests.
"""
from contextlib import contextmanager
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Build a database URL for the internal DB
DB_URL = (
    f"postgresql://{settings.internal_db.user}:{settings.internal_db.password}@"
    f"{settings.internal_db.host}:{settings.internal_db.port}/{settings.internal_db.database}"
)

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_db_connection() -> bool:
    """Return True if the internal DB is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return False


def init_db() -> None:
    """Create any required schema / migrations.

    For local dev we rely on Alembic or SQL scripts; this is a no-op placeholder.
    """
    logger.info("init_db called (no-op for local dev)")


@contextmanager
def get_db_context():
    """Yield a SQLAlchemy Session context manager."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db():
    """Generator-style DB dependency for FastAPI routes.

    Many modules import `get_db` from `backend.db.session` as a
    dependency. Provide a simple generator that yields a Session and
    ensures it's closed afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_db_connections() -> None:
    try:
        engine.dispose()
    except Exception:
        pass
"""Database session utilities for the backend package.

This is a minimal implementation used for local development and tests.
"""
from contextlib import contextmanager
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Build a database URL for the internal DB
DB_URL = (
    f"postgresql://{settings.internal_db.user}:{settings.internal_db.password}@"
    f"{settings.internal_db.host}:{settings.internal_db.port}/{settings.internal_db.database}"
)

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_db_connection() -> bool:
    """Return True if the internal DB is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return False


def init_db() -> None:
    """Create any required schema / migrations.

    For local dev we rely on Alembic or SQL scripts; this is a no-op placeholder.
    """
    logger.info("init_db called (no-op for local dev)")


@contextmanager
def get_db_context():
    """Yield a SQLAlchemy Session context manager."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db():
    """Generator-style DB dependency for FastAPI routes.

    Many modules import `get_db` from `backend.db.session` as a
    dependency. Provide a simple generator that yields a Session and
    ensures it's closed afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_db_connections() -> None:
    try:
        engine.dispose()
    except Exception:
        pass
