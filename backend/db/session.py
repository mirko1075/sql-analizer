"""
Database session management.

Handles database connections, session lifecycle, and connection pooling
for the internal AI Query Analyzer database (PostgreSQL).
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from backend.core.config import settings
from backend.core.logger import get_logger
from backend.db.models import Base

logger = get_logger(__name__)

# Database engine (singleton)
_engine = None
_SessionLocal = None


def get_engine():
    """
    Get or create the SQLAlchemy engine.

    Uses connection pooling for production efficiency.
    """
    global _engine

    if _engine is None:
        # Get database URL from settings
        db_url = settings.internal_db.get_connection_string('postgresql')

        logger.info(f"Creating database engine for: {settings.internal_db.host}:{settings.internal_db.port}")

        # Create engine with connection pooling
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,  # Verify connections before using them
            pool_size=10,  # Number of connections to maintain
            max_overflow=20,  # Additional connections when pool is exhausted
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False,  # Set to True for SQL query logging
        )

        logger.info("Database engine created successfully")

    return _engine


def get_session_factory():
    """
    Get or create the session factory.

    Returns a sessionmaker that creates new database sessions.
    """
    global _SessionLocal

    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        logger.info("Session factory created")

    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI route handlers to get a database session.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    The session is automatically closed after the request.
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions outside of FastAPI.

    Usage:
        with get_db_context() as db:
            items = db.query(Item).all()

    The session is automatically committed and closed.
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Check if the database is accessible.

    Returns:
        True if database is reachable, False otherwise
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection check: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"Database connection check: FAILED - {e}")
        return False


def init_db() -> None:
    """
    Initialize the database schema.

    Creates all tables defined in the models if they don't exist.
    This is safe to run multiple times (idempotent).
    """
    try:
        engine = get_engine()

        logger.info("Initializing database schema...")

        # Create all tables
        Base.metadata.create_all(bind=engine)

        logger.info("Database schema initialized successfully")

        # Log created tables
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        logger.info(f"Tables in database: {', '.join(tables)}")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def close_db_connections() -> None:
    """
    Close all database connections and dispose of the engine.

    Should be called during application shutdown.
    """
    global _engine, _SessionLocal

    if _SessionLocal is not None:
        logger.info("Closing database session factory")
        _SessionLocal = None

    if _engine is not None:
        logger.info("Disposing database engine and closing connections")
        _engine.dispose()
        _engine = None

    logger.info("All database connections closed")


def reset_db() -> None:
    """
    Drop and recreate all tables.

    WARNING: This will DELETE all data!
    Only use in development/testing.
    """
    if settings.env == 'production':
        raise RuntimeError("Cannot reset database in production environment!")

    logger.warning("RESETTING DATABASE - ALL DATA WILL BE LOST!")

    engine = get_engine()

    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    logger.info("All tables dropped")

    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    logger.info("All tables recreated")

    logger.warning("Database reset complete")
