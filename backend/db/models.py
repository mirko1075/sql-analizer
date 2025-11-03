"""
Simple SQLite database models for storing collected queries and analysis.
No multi-tenancy, no complex relationships - just the essentials.
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class SlowQuery(Base):
    """
    Stores slow queries collected from MySQL slow_log.
    """
    __tablename__ = 'slow_queries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Query information
    sql_text = Column(Text, nullable=False)
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
    analysis_result_id = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<SlowQuery(id={self.id}, time={self.query_time}s, analyzed={self.analyzed})>"


class AnalysisResult(Base):
    """
    Stores analysis results (rule-based + AI suggestions).
    """
    __tablename__ = 'analysis_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    slow_query_id = Column(Integer, nullable=False, index=True)
    
    # Rule-based analysis
    issues_found = Column(Text)  # JSON string of issues
    suggested_indexes = Column(Text)  # JSON string of index suggestions
    improvement_priority = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    
    # AI analysis from LLaMA
    ai_analysis = Column(Text)  # Full AI response
    ai_suggestions = Column(Text)  # Parsed AI suggestions
    
    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float)  # seconds
    
    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, priority={self.improvement_priority})>"


# Database setup
DB_PATH = os.getenv("DB_PATH", "/app/cache/dbpower.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
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
