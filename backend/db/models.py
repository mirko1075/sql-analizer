"""
SQLAlchemy ORM models for the AI Query Analyzer.

These models represent the internal database schema used to store
collected slow queries and their analysis results.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column, String, Integer, BigInteger, Float, DateTime, Text, JSON, Enum,
    ForeignKey, Index, CheckConstraint, Boolean, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class QueryStatus(enum.Enum):
    """Status of a slow query record."""
    NEW = "NEW"
    ANALYZED = "ANALYZED"
    IGNORED = "IGNORED"
    ERROR = "ERROR"


class ImprovementLevel(enum.Enum):
    """Level of potential improvement for a query."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnalysisMethod(enum.Enum):
    """Method used for query analysis."""
    RULE_BASED = "rule_based"
    AI_ASSISTED = "ai_assisted"
    HYBRID = "hybrid"


class SlowQueryRaw(Base):
    """
    Raw slow query records collected from monitored databases.

    Each row represents a single execution of a slow query.
    Queries are grouped by fingerprint for aggregate analysis.
    """
    __tablename__ = 'slow_queries_raw'

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source database information
    source_db_type = Column(String(20), nullable=False, index=True)  # 'mysql' or 'postgresql'
    source_db_host = Column(String(255), nullable=False, index=True)
    source_db_name = Column(String(255), nullable=False)
    source_db_port = Column(Integer)

    # Query identification
    fingerprint = Column(String(64), nullable=False, index=True)  # SHA-256 hash of normalized query
    full_sql = Column(Text, nullable=False)
    sql_hash = Column(String(64), nullable=False)  # SHA-256 hash of full SQL

    # Performance metrics
    duration_ms = Column(Numeric(12, 2), nullable=False, index=True)
    rows_examined = Column(BigInteger, default=0)
    rows_returned = Column(BigInteger, default=0)

    # EXPLAIN plan (if available)
    plan_json = Column(JSON)  # Parsed EXPLAIN output
    plan_text = Column(Text)  # Text format EXPLAIN output

    # Metadata
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    status = Column(
        Enum(QueryStatus),
        nullable=False,
        default=QueryStatus.NEW,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    analysis = relationship("AnalysisResult", back_populates="slow_query", uselist=False, cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_source_db', 'source_db_type', 'source_db_host'),
        Index('idx_fingerprint_db', 'fingerprint', 'source_db_type'),
        Index('idx_status_captured', 'status', 'captured_at'),
        Index('idx_duration', 'duration_ms'),
    )

    def __repr__(self):
        return f"<SlowQueryRaw(id={self.id}, db={self.source_db_type}, duration={self.duration_ms}ms)>"


class AnalysisResult(Base):
    """
    Analysis results for slow queries.

    Stores the output of the query analyzer including identified problems,
    root causes, and optimization suggestions.
    """
    __tablename__ = 'analysis_result'

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to slow query
    slow_query_id = Column(
        UUID(as_uuid=True),
        ForeignKey('slow_queries_raw.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True
    )

    # Analysis output
    problem = Column(String(500), nullable=False)
    root_cause = Column(Text, nullable=False)
    suggestions = Column(JSON, nullable=False)  # List of suggestion objects

    # Impact assessment
    improvement_level = Column(
        Enum(ImprovementLevel),
        nullable=False,
        index=True
    )
    estimated_speedup = Column(String(50))  # e.g., "10-100x", "2-5x"

    # Analysis metadata
    analyzer_version = Column(String(20), nullable=False, default="1.0.0")
    analysis_method = Column(
        Enum(AnalysisMethod),
        nullable=False,
        default=AnalysisMethod.RULE_BASED
    )
    confidence_score = Column(Numeric(3, 2), nullable=False)  # 0.00 to 1.00
    analysis_metadata = Column(JSON)  # Additional analysis data

    # Timestamps
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    slow_query = relationship("SlowQueryRaw", back_populates="analysis")

    # Indexes
    __table_args__ = (
        Index('idx_improvement_level', 'improvement_level'),
        Index('idx_analyzed_at', 'analyzed_at'),
    )

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, level={self.improvement_level.value})>"


class DbMetadata(Base):
    """
    Metadata about monitored databases.

    Stores information about the databases being monitored,
    including their schemas, tables, and indexes.
    """
    __tablename__ = 'db_metadata'

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Database identification
    db_type = Column(String(20), nullable=False)  # 'mysql' or 'postgresql'
    db_host = Column(String(255), nullable=False)
    db_name = Column(String(255), nullable=False)
    db_port = Column(Integer)

    # Schema information
    table_name = Column(String(255), nullable=False)
    column_info = Column(JSON)  # Column definitions
    index_info = Column(JSON)  # Index definitions
    row_count_estimate = Column(BigInteger)
    table_size_bytes = Column(BigInteger)

    # Timestamps
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_db_table', 'db_type', 'db_host', 'db_name', 'table_name', unique=True),
    )

    def __repr__(self):
        return f"<DbMetadata(db={self.db_type}:{self.db_name}, table={self.table_name})>"


class OptimizationHistory(Base):
    """
    History of optimization actions taken.

    Tracks when suggestions were applied and their effectiveness.
    This is part of the learning loop for continuous improvement.
    """
    __tablename__ = 'optimization_history'

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Reference to analysis
    analysis_id = Column(
        UUID(as_uuid=True),
        ForeignKey('analysis_result.id', ondelete='SET NULL'),
        index=True
    )

    # Optimization details
    optimization_type = Column(String(50), nullable=False)  # 'INDEX', 'REWRITE', 'SCHEMA', etc.
    sql_statement = Column(Text)  # The actual SQL executed (e.g., CREATE INDEX)
    applied_by = Column(String(100))  # User or system that applied it

    # Effectiveness tracking
    was_effective = Column(Boolean)
    before_duration_ms = Column(Numeric(12, 2))
    after_duration_ms = Column(Numeric(12, 2))
    improvement_ratio = Column(Numeric(6, 2))  # Speedup factor

    # Notes and metadata
    notes = Column(Text)
    optimization_metadata = Column(JSON)

    # Timestamps
    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    verified_at = Column(DateTime)  # When effectiveness was verified
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<OptimizationHistory(id={self.id}, type={self.optimization_type})>"


class SchemaVersion(Base):
    """
    Database schema version tracking.

    Used for database migrations and version management.
    """
    __tablename__ = 'schema_version'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Version information
    version = Column(String(20), nullable=False, unique=True)
    description = Column(String(500))

    # Migration script
    upgrade_script = Column(Text)
    downgrade_script = Column(Text)

    # Timestamps
    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<SchemaVersion(version={self.version})>"
