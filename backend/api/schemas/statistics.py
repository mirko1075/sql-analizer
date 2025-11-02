"""
Pydantic schemas for statistics API responses.
"""
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class DailyMetricPoint(BaseModel):
    """Single point in time-series data."""
    metric_date: datetime = Field(..., description="Metric date")
    source_db_type: str
    source_db_host: str
    total_queries: int
    unique_fingerprints: int
    avg_duration_ms: Optional[float] = None
    p95_duration_ms: Optional[float] = None
    p99_duration_ms: Optional[float] = None
    avg_rows_examined: Optional[int] = None
    avg_rows_returned: Optional[int] = None
    avg_efficiency_ratio: Optional[float] = None
    analyzed_count: int = 0
    high_impact_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PerformanceTrendsResponse(BaseModel):
    """Performance trends over time."""
    metrics: List[DailyMetricPoint]
    date_range: dict = Field(..., description="Start and end dates of the data")
    summary: dict = Field(..., description="Aggregate statistics across all data")


class TopQueryPattern(BaseModel):
    """Top query pattern by various metrics."""
    fingerprint: str
    source_db_type: str
    source_db_host: str
    execution_count: int
    total_duration_ms: Optional[float] = None
    avg_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    p95_duration_ms: Optional[float] = None
    avg_efficiency_ratio: Optional[float] = None
    improvement_level: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    representative_query_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class EfficiencyBucket(BaseModel):
    """Efficiency ratio histogram bucket."""
    range_label: str = Field(..., description="e.g., '1-10', '10-100', '>1000'")
    count: int
    percentage: float


class QueryDistributionResponse(BaseModel):
    """Query distribution statistics."""
    top_slowest: List[TopQueryPattern] = Field(..., description="Top 10 slowest queries by avg duration")
    top_frequent: List[TopQueryPattern] = Field(..., description="Top 10 most frequently executed queries")
    top_inefficient: List[TopQueryPattern] = Field(..., description="Top 10 queries with worst efficiency ratio")
    efficiency_histogram: List[EfficiencyBucket] = Field(..., description="Distribution of efficiency ratios")


class AIInsightQuery(BaseModel):
    """Query with AI analysis insights."""
    fingerprint: str
    source_db_type: str
    source_db_host: str
    execution_count: int
    avg_duration_ms: Optional[float] = None
    improvement_level: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    representative_query_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class AIInsightsResponse(BaseModel):
    """AI-driven insights and recommendations."""
    high_priority_queries: List[AIInsightQuery] = Field(..., description="Queries marked as HIGH or CRITICAL impact")
    recently_analyzed: List[AIInsightQuery] = Field(..., description="Most recently analyzed queries")
    total_analyzed: int = Field(..., description="Total count of queries with AI analysis")
    analysis_distribution: dict = Field(..., description="Count by improvement level")
