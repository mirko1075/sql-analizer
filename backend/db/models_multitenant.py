"""
Multi-tenant database models for DBPower AI Cloud.
Supports Organization -> Team -> Identity hierarchy with RBAC.
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, DateTime,
    Boolean, ForeignKey, Index, UniqueConstraint, JSON, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import os
import enum
import secrets
import hashlib

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    SUPER_ADMIN = "super_admin"  # Global admin, manages all organizations
    ORG_ADMIN = "org_admin"      # Organization admin, manages org resources
    TEAM_LEAD = "team_lead"      # Team leader, manages team resources
    USER = "user"                # Regular user, view assigned resources


class QueryStatus(str, enum.Enum):
    """Query analysis status."""
    PENDING = "pending"          # Just collected, needs review
    ANALYZED = "analyzed"        # Analysis completed, waiting for action
    ARCHIVED = "archived"        # Marked as not interesting
    RESOLVED = "resolved"        # Issue fixed or acknowledged as OK


class PriorityLevel(str, enum.Enum):
    """Priority levels for analysis results."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# MULTI-TENANT HIERARCHY
# ============================================================================

class Organization(Base):
    """
    Top-level tenant. Each organization is completely isolated.
    Represents a company/customer using the service.
    """
    __tablename__ = 'organizations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)

    # Settings (JSON for flexibility)
    settings = Column(JSON, default={})

    # API Key management (hashed)
    api_key_hash = Column(String(128), nullable=True, index=True)
    api_key_created_at = Column(DateTime, nullable=True)
    api_key_expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    slow_queries = relationship("SlowQuery", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"

    def generate_api_key(self) -> str:
        """Generate a new API key for this organization."""
        api_key = f"dbp_{self.id}_{secrets.token_urlsafe(32)}"
        self.api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self.api_key_created_at = datetime.utcnow()
        self.api_key_expires_at = datetime.utcnow() + timedelta(days=365)
        return api_key  # Return plain text key ONCE (store it!)

    def verify_api_key(self, api_key: str) -> bool:
        """Verify an API key against the stored hash."""
        if not self.api_key_hash:
            return False
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return key_hash == self.api_key_hash


class Team(Base):
    """
    Second level of hierarchy. Teams belong to an organization.
    Represents departments or groups within a company.
    """
    __tablename__ = 'teams'

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="teams")
    identities = relationship("Identity", back_populates="team", cascade="all, delete-orphan")
    slow_queries = relationship("SlowQuery", back_populates="team", cascade="all, delete-orphan")

    # Unique constraint: team name must be unique within organization
    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_org_team_name'),
        Index('idx_org_team', 'organization_id', 'name'),
    )

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}', org_id={self.organization_id})>"


class Identity(Base):
    """
    Third level of hierarchy. Identities are subgroups within teams.
    Allows fine-grained resource allocation (e.g., by database, by project).
    """
    __tablename__ = 'identities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="identities")
    users = relationship("User", back_populates="identity", cascade="all, delete-orphan")
    slow_queries = relationship("SlowQuery", back_populates="identity", cascade="all, delete-orphan")

    # Unique constraint: identity name must be unique within team
    __table_args__ = (
        UniqueConstraint('team_id', 'name', name='uq_team_identity_name'),
        Index('idx_team_identity', 'team_id', 'name'),
    )

    def __repr__(self):
        return f"<Identity(id={self.id}, name='{self.name}', team_id={self.team_id})>"


# ============================================================================
# USERS AND AUTHENTICATION
# ============================================================================

class User(Base):
    """
    User accounts with role-based access control.
    Users belong to an organization and optionally to an identity.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    identity_id = Column(Integer, ForeignKey('identities.id', ondelete='SET NULL'), nullable=True, index=True)

    # Authentication
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER, index=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    identity = relationship("Identity", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role={self.role})>"


# ============================================================================
# QUERY MANAGEMENT (with multi-tenancy)
# ============================================================================

class SlowQuery(Base):
    """
    Stores slow queries collected from client agents.
    Each query is associated with an organization, team, and identity.
    """
    __tablename__ = 'slow_queries'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant fields
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True)
    identity_id = Column(Integer, ForeignKey('identities.id', ondelete='CASCADE'), nullable=False, index=True)

    # Query information (ANONYMIZED)
    sql_text = Column(Text, nullable=False)  # Anonymized SQL
    sql_fingerprint = Column(String(64), nullable=False, index=True)  # MD5 hash for grouping

    # Performance metrics
    query_time = Column(Float, nullable=False)  # seconds
    lock_time = Column(Float, default=0.0)
    rows_sent = Column(Integer, default=0)
    rows_examined = Column(Integer, default=0)

    # Metadata
    database_name = Column(String(255))
    user_host = Column(String(255))
    start_time = Column(DateTime, default=datetime.utcnow)
    collected_at = Column(DateTime, default=datetime.utcnow)

    # Analysis status
    analyzed = Column(Boolean, default=False)
    status = Column(Enum(QueryStatus), nullable=False, default=QueryStatus.PENDING, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="slow_queries")
    team = relationship("Team", back_populates="slow_queries")
    identity = relationship("Identity", back_populates="slow_queries")
    analysis_result = relationship("AnalysisResult", back_populates="slow_query", uselist=False, cascade="all, delete-orphan")

    # Indexes for performance and uniqueness
    __table_args__ = (
        UniqueConstraint('organization_id', 'sql_fingerprint', 'start_time', name='uq_org_query_time'),
        Index('idx_org_status_collected', 'organization_id', 'status', 'collected_at'),
        Index('idx_team_status', 'team_id', 'status'),
        Index('idx_identity_status', 'identity_id', 'status'),
    )

    def __repr__(self):
        return f"<SlowQuery(id={self.id}, time={self.query_time}s, status={self.status.value})>"


class AnalysisResult(Base):
    """
    Stores analysis results (rule-based + AI suggestions).
    One-to-one relationship with SlowQuery.
    """
    __tablename__ = 'analysis_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    slow_query_id = Column(Integer, ForeignKey('slow_queries.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)

    # Rule-based analysis
    issues_found = Column(JSON)  # List of issues
    suggested_indexes = Column(JSON)  # List of index suggestions
    improvement_priority = Column(Enum(PriorityLevel), nullable=False, default=PriorityLevel.LOW)

    # AI analysis
    ai_analysis = Column(Text)  # Full AI response
    ai_suggestions = Column(JSON)  # Parsed AI suggestions
    ai_provider = Column(String(50))  # Which AI provider was used (llama, openai, anthropic)

    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float)  # seconds

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    slow_query = relationship("SlowQuery", back_populates="analysis_result")

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, priority={self.improvement_priority.value})>"


# ============================================================================
# AUDIT LOGGING
# ============================================================================

class AuditLog(Base):
    """
    Immutable audit log for compliance.
    Records all significant actions (API calls, data access, changes).
    """
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Who
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)

    # What
    action = Column(String(100), nullable=False, index=True)  # e.g., "query.create", "user.login"
    resource_type = Column(String(50), nullable=True)  # e.g., "slow_query", "user"
    resource_id = Column(Integer, nullable=True)

    # Context
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, etc.
    request_path = Column(String(500), nullable=True)

    # Result
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Details (JSON for flexibility)
    details = Column(JSON, default={})

    # When
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")

    # Indexes for query performance
    __table_args__ = (
        Index('idx_org_timestamp', 'organization_id', 'timestamp'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_action_timestamp', 'action', 'timestamp'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', timestamp={self.timestamp})>"


# ============================================================================
# DATABASE SETUP
# ============================================================================

def get_database_url() -> str:
    """
    Get database URL from environment.
    Supports both PostgreSQL (production) and SQLite (development).
    """
    # Check for explicit DATABASE_URL (e.g., from cloud providers)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Fix common issue with Heroku PostgreSQL URLs
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url

    # Build from components
    db_type = os.getenv("DB_TYPE", "postgresql")

    if db_type == "sqlite":
        # Development mode
        db_path = os.getenv("DB_PATH", "/app/cache/dbpower_multitenant.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return f"sqlite:///{db_path}"

    # PostgreSQL (production)
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "dbpower")
    db_user = os.getenv("DB_USER", "dbpower")
    db_password = os.getenv("DB_PASSWORD", "")

    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


# Create engine with connection pooling
DATABASE_URL = get_database_url()
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,  # Verify connections before using
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session (dependency injection for FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
