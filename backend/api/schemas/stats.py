"""
Pydantic schemas for statistics API responses.
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class TableImpactSchema(BaseModel):
    """Schema for table impact statistics."""
    source_db_type: str
    source_db_host: str
    table_name: str
    query_count: int = Field(..., description="Number of slow queries involving this table")
    avg_duration_ms: float = Field(..., description="Average execution time for queries on this table")
    distinct_queries: int = Field(..., description="Number of distinct query patterns")

    class Config:
        from_attributes = True


class DatabaseStatsSchema(BaseModel):
    """Overall database statistics."""
    source_db_type: str
    source_db_host: str
    total_slow_queries: int
    analyzed_queries: int
    pending_queries: int
    avg_duration_ms: float
    high_impact_count: int = Field(..., description="Queries with HIGH or CRITICAL improvement potential")


class QueryTrendSchema(BaseModel):
    """Query performance trend over time."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    query_count: int
    avg_duration_ms: float
    max_duration_ms: float


class ImprovementSummarySchema(BaseModel):
    """Summary of potential improvements."""
    improvement_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    count: int = Field(..., description="Number of queries in this category")
    avg_potential_speedup: Optional[str] = None


class GlobalStatsResponse(BaseModel):
    """Global statistics response."""
    total_slow_queries: int
    total_analyzed: int
    total_pending: int
    databases_monitored: int
    top_tables: List[TableImpactSchema]
    improvement_summary: List[ImprovementSummarySchema]
    recent_trend: List[QueryTrendSchema]

    class Config:
        from_attributes = True


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status: healthy, degraded, unhealthy")
    version: str = Field(..., description="Application version")
    database: Dict[str, str] = Field(..., description="Database connection status")
    redis: Dict[str, str] = Field(..., description="Redis connection status")
    uptime_seconds: Optional[float] = None
    timestamp: str

    class Config:
        from_attributes = True
