"""Minimal SQLAlchemy models used by the backend routes.

These are simplified versions intended to let the application import the
models during local development and tests. The actual project likely has a
full models module; this shim provides the attributes referenced by the
routes so the app can start without a real database schema present.
"""
from datetime import datetime
import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SlowQueryRaw(Base):
    __tablename__ = "slow_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint = Column(String, nullable=False)
    source_db_type = Column(String, nullable=True)
    source_db_host = Column(String, nullable=True)
    source_db_name = Column(String, nullable=True)
    duration_ms = Column(Float, nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="NEW")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slow_query_id = Column(UUID(as_uuid=True), ForeignKey("slow_queries.id"))
    improvement_level = Column(String, nullable=True)
    suggestions = Column(String, nullable=True)

    slow_query = relationship("SlowQueryRaw", backref="analysis_results")


class DbMetadata(Base):
    __tablename__ = "db_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    db_type = Column(String, nullable=False)
    db_host = Column(String, nullable=False)
    db_name = Column(String, nullable=False)


__all__ = ["Base", "SlowQueryRaw", "AnalysisResult", "DbMetadata"]
"""Minimal SQLAlchemy models used by the backend routes.

These are simplified versions intended to let the application import the
models during local development and tests. The actual project likely has a
full models module; this shim provides the attributes referenced by the
routes so the app can start without a real database schema present.
"""
from datetime import datetime
import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SlowQueryRaw(Base):
    __tablename__ = "slow_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint = Column(String, nullable=False)
    source_db_type = Column(String, nullable=True)
    source_db_host = Column(String, nullable=True)
    duration_ms = Column(Float, nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="NEW")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slow_query_id = Column(UUID(as_uuid=True), ForeignKey("slow_queries.id"))
    improvement_level = Column(Integer, nullable=True)
    suggestions = Column(String, nullable=True)

    slow_query = relationship("SlowQueryRaw", backref="analysis_results")


__all__ = ["Base", "SlowQueryRaw", "AnalysisResult"]
