"""
Pydantic schemas for slow query API responses.

These schemas define the structure of data returned by the API endpoints.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class SlowQueryBase(BaseModel):
    """Base schema for slow query data."""
    source_db_type: str = Field(..., description="Database type: mysql, postgres, oracle, sqlserver")
    source_db_host: str = Field(..., description="Database host")
    source_db_name: str = Field(..., description="Database name")
    fingerprint: str = Field(..., description="Normalized query fingerprint")
    full_sql: str = Field(..., description="Original SQL query")
    duration_ms: Decimal = Field(..., description="Query execution time in milliseconds")
    rows_examined: Optional[int] = Field(None, description="Number of rows examined")
    rows_returned: Optional[int] = Field(None, description="Number of rows returned")
    status: str = Field(..., description="Query status: NEW, ANALYZED, IGNORED, ERROR")


class SlowQuerySummary(BaseModel):
    """Summary of slow queries grouped by fingerprint."""
    id: str = Field(..., description="Representative query ID (most recent execution)")
    fingerprint: str = Field(..., description="Query fingerprint")
    source_db_type: str
    source_db_host: str
    execution_count: int = Field(..., description="Number of times this query executed")
    avg_duration_ms: float = Field(..., description="Average execution time")
    min_duration_ms: float = Field(..., description="Minimum execution time")
    max_duration_ms: float = Field(..., description="Maximum execution time")
    p95_duration_ms: Optional[float] = Field(None, description="95th percentile execution time")
    last_seen: datetime = Field(..., description="Last execution timestamp")
    has_analysis: bool = Field(..., description="Whether this query has been analyzed")
    max_improvement_level: Optional[str] = Field(None, description="Highest improvement level: LOW, MEDIUM, HIGH, CRITICAL")

    model_config = ConfigDict(from_attributes=True)


class SlowQueryDetail(SlowQueryBase):
    """Detailed slow query information including ID and timestamps."""
    id: UUID
    sql_hash: Optional[str] = None
    plan_json: Optional[Dict[str, Any]] = Field(None, description="Execution plan in JSON format")
    plan_text: Optional[str] = Field(None, description="Raw EXPLAIN output")
    captured_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuggestionSchema(BaseModel):
    """Schema for optimization suggestion."""
    type: str = Field(..., description="Suggestion type: INDEX, REWRITE, PARTITION, etc.")
    priority: str = Field(..., description="Priority: LOW, MEDIUM, HIGH, CRITICAL")
    sql: Optional[str] = Field(None, description="SQL statement to apply the suggestion")
    description: str = Field(..., description="Human-readable description")
    estimated_impact: Optional[str] = Field(None, description="Expected performance improvement")


class AnalysisResultSchema(BaseModel):
    """Schema for query analysis result."""
    id: UUID
    slow_query_id: UUID
    problem: str = Field(..., description="Problem description")
    root_cause: str = Field(..., description="Technical explanation")
    suggestions: List[SuggestionSchema] = Field(..., description="List of optimization suggestions")
    improvement_level: Optional[str] = Field(None, description="Impact level: LOW, MEDIUM, HIGH, CRITICAL")
    estimated_speedup: Optional[str] = Field(None, description="Estimated performance gain")
    analyzer_version: Optional[str] = None
    analysis_method: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIRecommendationSchema(BaseModel):
    """Schema for AI-generated recommendation entry."""
    type: Optional[str] = Field(None, description="Recommendation category")
    priority: Optional[str] = Field(None, description="Suggested priority")
    description: Optional[str] = Field(None, description="Detailed recommendation text")
    sql: Optional[str] = Field(None, description="SQL snippet provided by the AI")
    estimated_impact: Optional[str] = Field(None, description="Expected impact or speedup")
    rationale: Optional[str] = Field(None, description="Reasoning behind the recommendation")


class AIAnalysisResultSchema(BaseModel):
    """Schema for AI (LLM) analysis result."""
    id: UUID
    slow_query_id: UUID
    provider: str
    model: str
    summary: str
    root_cause: str
    recommendations: List[AIRecommendationSchema] = Field(default_factory=list)
    improvement_level: Optional[str] = Field(None, description="Impact level suggested by AI")
    estimated_speedup: Optional[str] = Field(None, description="Estimated performance gain suggested by AI")
    confidence_score: Optional[Decimal] = Field(None, description="AI confidence in results")
    prompt_metadata: Optional[Dict[str, Any]] = None
    provider_response: Optional[Dict[str, Any]] = None
    analyzed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SlowQueryWithAnalysis(SlowQueryDetail):
    """Slow query with its analysis result."""
    analysis: Optional[AnalysisResultSchema] = None
    ai_analysis: Optional[AIAnalysisResultSchema] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)


class SlowQueryListResponse(BaseModel):
    """Response for list of slow queries."""
    items: List[SlowQuerySummary]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)
