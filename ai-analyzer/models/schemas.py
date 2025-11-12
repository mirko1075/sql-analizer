"""
Pydantic schemas for AI Analyzer API.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class IssueSeverity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    """Issue categories."""
    PERFORMANCE = "performance"
    INDEXING = "indexing"
    QUERY_STRUCTURE = "query_structure"
    N_PLUS_ONE = "n_plus_one"
    FULL_TABLE_SCAN = "full_table_scan"
    MISSING_INDEX = "missing_index"
    SUBOPTIMAL_JOIN = "suboptimal_join"
    EXCESSIVE_DATA = "excessive_data"
    OTHER = "other"


class AnalysisIssue(BaseModel):
    """Issue found in SQL query analysis."""
    severity: IssueSeverity
    category: IssueCategory
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    suggestion: str = Field(..., min_length=1)
    estimated_impact: Optional[str] = None  # e.g., "50% faster", "Reduces I/O"

    class Config:
        json_schema_extra = {
            "example": {
                "severity": "high",
                "category": "missing_index",
                "title": "Missing index on user_id column",
                "description": "The query performs a full table scan on the orders table filtering by user_id.",
                "suggestion": "CREATE INDEX idx_orders_user_id ON orders(user_id);",
                "estimated_impact": "70% query time reduction"
            }
        }


class AnalysisRequest(BaseModel):
    """Request for SQL query analysis."""
    sql_query: str = Field(..., min_length=1, max_length=10000)
    database_type: Optional[str] = Field(default="postgresql", pattern="^(mysql|postgresql|sqlite|oracle|mssql)$")
    execution_time_ms: Optional[float] = Field(default=None, ge=0)
    rows_examined: Optional[int] = Field(default=None, ge=0)
    rows_returned: Optional[int] = Field(default=None, ge=0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "sql_query": "SELECT * FROM users WHERE email LIKE '%@example.com%' ORDER BY created_at DESC",
                "database_type": "postgresql",
                "execution_time_ms": 2500.5,
                "rows_examined": 100000,
                "rows_returned": 50
            }
        }


class AnalysisResponse(BaseModel):
    """Response from SQL query analysis."""
    query_id: str = Field(..., description="Unique identifier for this analysis")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    issues_found: int = Field(..., ge=0)
    issues: List[AnalysisIssue] = Field(default_factory=list)
    overall_assessment: str = Field(..., min_length=1)
    optimization_priority: IssueSeverity = Field(default=IssueSeverity.INFO)
    estimated_improvement: Optional[str] = None
    ai_model_used: str
    analysis_time_ms: float = Field(..., ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "analyzed_at": "2024-01-15T10:30:00Z",
                "issues_found": 2,
                "issues": [
                    {
                        "severity": "high",
                        "category": "full_table_scan",
                        "title": "Full table scan with LIKE pattern",
                        "description": "Using LIKE with leading wildcard prevents index usage",
                        "suggestion": "Use full-text search or reconsider query pattern",
                        "estimated_impact": "80% performance improvement"
                    }
                ],
                "overall_assessment": "Query has significant performance issues that should be addressed",
                "optimization_priority": "high",
                "estimated_improvement": "80% faster execution",
                "ai_model_used": "gpt-4",
                "analysis_time_ms": 1250.5
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy")
    service: str
    version: str
    model_provider: str
    model_name: str
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "dbpower-ai-analyzer",
                "version": "1.0.0",
                "model_provider": "openai",
                "model_name": "gpt-4",
                "uptime_seconds": 3600.5,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class BatchAnalysisRequest(BaseModel):
    """Request for batch SQL query analysis."""
    queries: List[AnalysisRequest] = Field(..., min_items=1, max_items=100)
    parallel: bool = Field(default=True, description="Process queries in parallel")

    class Config:
        json_schema_extra = {
            "example": {
                "queries": [
                    {
                        "sql_query": "SELECT * FROM users WHERE id = 1",
                        "database_type": "postgresql"
                    },
                    {
                        "sql_query": "SELECT * FROM orders WHERE user_id IN (SELECT id FROM users)",
                        "database_type": "mysql"
                    }
                ],
                "parallel": True
            }
        }


class BatchAnalysisResponse(BaseModel):
    """Response from batch SQL query analysis."""
    total_queries: int = Field(..., ge=0)
    successful: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    results: List[AnalysisResponse] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    total_analysis_time_ms: float = Field(..., ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "total_queries": 2,
                "successful": 2,
                "failed": 0,
                "results": [],
                "errors": [],
                "total_analysis_time_ms": 2500.5
            }
        }
